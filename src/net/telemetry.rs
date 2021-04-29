use serde::Serialize;

use crate::hardware::AfeGain;

#[derive(Copy, Clone)]
pub struct TelemetryBuffer {
    pub latest_samples: [i16; 2],
    pub latest_outputs: [i16; 2],
    pub digital_inputs: [bool; 2],
}

#[derive(Serialize)]
pub struct Telemetry {
    input_levels: [f32; 2],
    output_levels: [f32; 2],
    digital_inputs: [bool; 2]
}

impl Default for TelemetryBuffer {
    fn default() -> Self {
        Self {
            latest_samples: [0, 0],
            latest_outputs: [0, 0],
            digital_inputs: [false, false],
        }
    }
}

impl TelemetryBuffer {
    pub fn to_telemetry(self, afe0: AfeGain, afe1: AfeGain) -> Telemetry {
        let in0_volts = self.latest_samples[0] as f32 / (i16::MAX as f32 * 5.0 * afe0.to_multiplier() as f32) * 4.096;
        let in1_volts = self.latest_samples[1] as f32 / (i16::MAX as f32 * 5.0 * afe1.to_multiplier() as f32) * 4.096;

        let out0_volts = self.latest_outputs[0] as f32 / (i16::MAX as f32) * 10.24;
        let out1_volts = self.latest_outputs[1] as f32 / (i16::MAX as f32) * 10.24;

        Telemetry {
            input_levels: [in0_volts, in1_volts],
            output_levels: [out0_volts, out1_volts],
            digital_inputs: self.digital_inputs,
        }
    }
}
