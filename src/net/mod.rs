///! Stabilizer network management module
///!
///! # Design
///! The stabilizer network architecture supports numerous layers to permit transmission of
///! telemetry (via MQTT), configuration of run-time settings (via MQTT + Miniconf), and live data
///! streaming over raw UDP/TCP sockets. This module encompasses the main processing routines
///! related to Stabilizer networking operations.
use heapless::{consts, String};
use miniconf::Miniconf;
use serde::Serialize;

use core::fmt::Write;

mod messages;
mod miniconf_client;
mod shared;
mod network_processor;
mod telemetry;

use crate::hardware::{CycleCounter, EthernetPhy, NetworkStack};
use messages::{MqttMessage, SettingsResponse};

pub use miniconf_client::MiniconfClient;
pub use shared::NetworkManager;
pub use network_processor::NetworkProcessor;
pub use telemetry::{Telemetry, TelemetryBuffer, TelemetryClient};

pub type NetworkReference = shared::NetworkStackProxy<'static, NetworkStack>;

#[derive(Copy, Clone, PartialEq)]
pub enum UpdateState {
    NoChange,
    Updated,
}

/// A structure of Stabilizer's default network users.
pub struct NetworkUsers<S: Default + Clone + Miniconf, T: Serialize> {
    pub miniconf: MiniconfClient<S>,
    pub processor: NetworkProcessor,
    pub telemetry: TelemetryClient<T>,
}

impl<S, T> NetworkUsers<S, T>
where
    S: Default + Clone + Miniconf,
    T: Serialize,
{
    /// Construct Stabilizer's default network users.
    ///
    /// # Args
    /// * `stack` - The network stack that will be used to share with all network users.
    /// * `phy` - The ethernet PHY connecting the network.
    /// * `cycle_counter` - The clock used for measuring time in the network.
    /// * `app` - The name of the application.
    /// * `mac` - The MAC address of the network.
    ///
    /// # Returns
    /// A new struct of network users.
    pub fn new(
        stack: NetworkStack,
        phy: EthernetPhy,
        cycle_counter: CycleCounter,
        app: &str,
        mac: smoltcp_nal::smoltcp::wire::EthernetAddress,
    ) -> Self {
        let stack_manager =
            cortex_m::singleton!(: NetworkManager = NetworkManager::new(stack))
                .unwrap();

        let processor = NetworkProcessor::new(
            stack_manager.acquire_stack(),
            phy,
            cycle_counter,
        );

        let prefix = get_device_prefix(app, mac);

        let settings = MiniconfClient::new(
            stack_manager.acquire_stack(),
            &get_client_id(app, "settings", mac),
            &prefix,
        );

        let telemetry = TelemetryClient::new(
            stack_manager.acquire_stack(),
            &get_client_id(app, "tlm", mac),
            &prefix,
        );

        NetworkUsers {
            miniconf: settings,
            processor,
            telemetry,
        }
    }

    /// Update and process all of the network users state.
    ///
    /// # Returns
    /// An indication if any of the network users indicated a state change.
    pub fn update(&mut self) -> UpdateState {
        // Poll for incoming data.
        let poll_result = self.processor.update();

        // Update the MQTT clients.
        self.telemetry.update();

        match self.miniconf.update() {
            UpdateState::Updated => UpdateState::Updated,
            UpdateState::NoChange => poll_result,
        }
    }
}

/// Get an MQTT client ID for a client.
///
/// # Args
/// * `app` - The name of the application
/// * `client` - The unique tag of the client
/// * `mac` - The MAC address of the device.
///
/// # Returns
/// A client ID that may be used for MQTT client identification.
fn get_client_id(
    app: &str,
    client: &str,
    mac: smoltcp_nal::smoltcp::wire::EthernetAddress,
) -> String<consts::U64> {
    let mac_string = {
        let mut mac_string: String<consts::U32> = String::new();
        let mac = mac.as_bytes();

        // Note(unwrap): 32-bytes is guaranteed to be valid for any mac address, as the address has
        // a fixed length.
        write!(
            &mut mac_string,
            "{:02x}-{:02x}-{:02x}-{:02x}-{:02x}-{:02x}",
            mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]
        )
        .unwrap();

        mac_string
    };

    let mut identifier = String::new();
    write!(&mut identifier, "{}-{}-{}", app, mac_string, client).unwrap();
    identifier
}

/// Get the MQTT prefix of a device.
///
/// # Args
/// * `app` - The name of the application that is executing.
/// * `mac` - The ethernet MAC address of the device.
///
/// # Returns
/// The MQTT prefix used for this device.
pub fn get_device_prefix(
    app: &str,
    mac: smoltcp_nal::smoltcp::wire::EthernetAddress,
) -> String<consts::U128> {
    let mac_string = {
        let mut mac_string: String<consts::U32> = String::new();
        let mac = mac.as_bytes();

        // Note(unwrap): 32-bytes is guaranteed to be valid for any mac address, as the address has
        // a fixed length.
        write!(
            &mut mac_string,
            "{:02x}-{:02x}-{:02x}-{:02x}-{:02x}-{:02x}",
            mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]
        )
        .unwrap();

        mac_string
    };

    // Note(unwrap): The mac address + binary name must be short enough to fit into this string. If
    // they are defined too long, this will panic and the device will fail to boot.
    let mut prefix: String<consts::U128> = String::new();
    write!(&mut prefix, "dt/sinara/{}/{}", app, mac_string).unwrap();

    prefix
}
