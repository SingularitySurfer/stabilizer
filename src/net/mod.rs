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

mod data_stream;
mod messages;
mod miniconf_client;
mod network_processor;
mod shared;
mod telemetry;

pub use data_stream::BlockGenerator;

use crate::hardware::{CycleCounter, EthernetPhy, NetworkStack};
use data_stream::DataStream;
use messages::{MqttMessage, SettingsResponse};

pub use miniconf_client::MiniconfClient;
pub use network_processor::NetworkProcessor;
pub use shared::NetworkManager;
use smoltcp_nal::embedded_nal::SocketAddr;
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
    processor: NetworkProcessor,
    stream: DataStream,
    generator: Option<BlockGenerator>,
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

        let (generator, stream) =
            data_stream::setup_streaming(stack_manager.acquire_stack());

        NetworkUsers {
            miniconf: settings,
            processor,
            telemetry,
            stream,
            generator: Some(generator),
        }
    }

    /// Enable live data streaming.
    pub fn enable_streaming(&mut self, remote: SocketAddr) -> BlockGenerator {
        self.stream.set_remote(remote);
        self.generator.take().unwrap()
    }

    pub fn direct_stream(&mut self, remote: SocketAddr) {
        if self.generator.is_none() {
            self.stream.set_remote(remote);
        }
    }

    pub fn update_stream(&mut self) {
        // Update the data stream.
        if self.generator.is_none() {
            loop {
                // Process egress of the stack.
                self.processor.egress();

                if !self.stream.process() {
                    return
                }
            }
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

        // Update the data stream.
        self.update_stream();

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
    let mut identifier = String::new();
    write!(&mut identifier, "{}-{}-{}", app, mac, client).unwrap();
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
    // Note(unwrap): The mac address + binary name must be short enough to fit into this string. If
    // they are defined too long, this will panic and the device will fail to boot.
    let mut prefix: String<consts::U128> = String::new();
    write!(&mut prefix, "dt/sinara/{}/{}", app, mac).unwrap();

    prefix
}
