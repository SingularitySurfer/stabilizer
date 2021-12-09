import matplotlib.pyplot as plt
from scipy import signal
import numpy as np
from math import pi
from dual_iir_configuration import calculate_pid_coefficients

class iirClass:
    def __init__(self):
        self.Kp = 0
        self.Ki = 0
        self.Kii = 0
        self.Kd = 0
        self.Kdd = 0
        self.y_min = 0
        self.y_max = 0
        self.y_offset = 0
        self.ba = [0, 0, 0, 0, 0]
        self.sampling_time = 10e-9*208
        self.sampling_freq = 1/self.sampling_time
        
    def compute_coeff(self):
        sampling_time = 10e-9*208
        self.ba = calculate_pid_coefficients(sampling_time, self)
        
    def freqz(self, points, xlim=None):
        b = np.zeros(int((len(self.ba)+1)/2))
        b = self.ba[0:len(b)]
        # calculate_pid_coefficients defines negative 'a' coefficients
        # for stabilizer onboard filter -> convert them back
        # it also omits a0 -> ba = [b0, b1, b2, -a1, -a2]
        a = (-1)*np.ones(len(self.ba)-len(b)+1)
        a[1:] = self.ba[len(b):]
        a = a*(-1)
        
        # get rid of divide by 0 warning of freqz
        a[0] = 1+1e-12

        #freqz defines transfer funcation as:
        #            jw                 -jw              -jwM
        #   jw    B(e  )    b[0] + b[1]e    + ... + b[M]e
        #H(e  ) = ------ = -----------------------------------
        #            jw                 -jw              -jwN
        #         A(e  )    a[0] + a[1]e    + ... + a[N]e

        # stabilizer as (a0=1)*y0 = a1*y1 + a2*y2 + b0*x0 + b1*x1 + b2*x2



        f, h = signal.freqz(b, a, points, fs=self.sampling_freq)
    
        fig, ax = plt.subplots(2, figsize=(12,8),constrained_layout=False)
        ax[0].semilogx(f, 20 * np.log10(np.maximum(abs(h), 1e-5)))
        phi = np.unwrap( 2*np.angle(h, deg=False))/2
        ax[1].semilogx(f, 360/(2*np.pi)*phi)

        if xlim is not None:
            ax[0].set_xlim(xlim)

        if xlim is not None:
            ax[1].set_xlim(xlim)
        
        ax[0].set_title('IIR filter frequency response')
        ax[0].set_ylabel('Amplitude [dB]')
        ax[1].set_ylabel('Phase [deg]')
        ax[1].set_xlabel('Frequency [Hz]')
        ax[0].grid(which='both', axis='both')
        ax[1].grid(which='both', axis='both')
        plt.show()


iir_ctrl=iirClass()
iir_ctrl.Kp = 1
iir_ctrl.Ki = 1
iir_ctrl.Kd = 0
iir_ctrl.y_min = -10
iir_ctrl.y_max = 10
iir_ctrl.compute_coeff()
iir_ctrl.y_offset = 0                         
iir_ctrl.freqz(10000)
