# Copyright (c) 2012-2015 by the GalSim developers team on GitHub
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
# https://github.com/GalSim-developers/GalSim
#
# GalSim is free software: redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the following
# conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions, and the disclaimer given in the accompanying LICENSE
#    file.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions, and the disclaimer given in the documentation
#    and/or other materials provided with the distribution.
#
"""@file atmpsf.py
Module for generating atmospheric PSFs using an autoregressive phase screen generator.

Relevant SPIE paper:
"Remembrance of phases past: An autoregressive method for generating realistic atmospheres in
simulations"
Srikar Srinath, Univ. of California, Santa Cruz;
Lisa A. Poyneer, Lawrence Livermore National Lab.;
Alexander R. Rudy, UCSC; S. Mark Ammons, LLNL
Published in Proceedings Volume 9148: Adaptive Optics Systems IV
September 2014

"""

import numpy as np
import galsim
import utilities
from galsim import GSObject


class AtmosphericPhaseGenerator(object):
    """ Create a an autoregressive atmospheric turbulence phase generator.

    @param time_step in seconds [Default: 0.03]
    @param screen_size in meters [Default: 10]
    @param screen_scale in meters [Default: 0.1]
    @param r0 in meters [Default: 0.2]
    @param alpha [Default: 0.999]
    @param velocity in meters/second [Default: 0]
    @param direction CCW relative to +x as galsim.Angle [Default: 0*galsim.degrees]

    The implicit atmosphere model here is that turbulence is confined to a set
    of 2D phase screens at different altitudes. The number of atmosphere layers
    is determined from the length of the `r0`, `velocity`, or `direction`
    arguments, if they are lists. If these arguments have different lengths
    then we ...FIXME...?

    Some suggestions for choices of wind velocities come from data hosted by
    NOAA. The Global Data Assimilation System (GDAS), run by the NOAA National
    Center for Environmental Prediction (NCEP), puts out various datasets. GDAS
    produces analyses every six hours, giving a large number of parameters
    tabulated at 24 altitudes in the atmosphere covering the entire Earth. The
    following is an example of wind velocities extracted from a file for 2014,
    Feb 13, 6h UT at the longitude and latitude of CTIO.
    (Wind velocities are m/s). Altitudes are approximate.
        Altitude (km)    velocity (m/s)    direction (deg.)
            1               0.98                -66
            10              0.67                116
            30              18.0                 27
    Data is found here: ftp://arlftp.arlhq.noaa.gov/pub/archives/gdas1/
    Datat documentation: http://ready.arl.noaa.gov/gdas1.php
    """
    def __init__(self, time_step=0.03, screen_size=10.0, screen_scale=0.1,
                 r0=0.2, alpha_mag=0.999, velocity=0.0, direction=0*galsim.degrees,
                 rng=None):
        if rng is None:
            rng = galsim.BaseDeviate()
        self.rng = rng
        self.size = int(np.ceil(screen_size/screen_scale))

        self.screen_scale = screen_scale
        self.pl, self.alpha = create_multilayer_arbase(self.size, screen_scale, 1./time_step,
                                                       r0, velocity, direction, alpha_mag)
        self._phaseFT = None

    def next(self):
        shape = self.alpha[0].shape
        self.phase = np.zeros(shape)
        for powerlaw, alpha in zip(self.pl, self.alpha):
            gd = galsim.GaussianDeviate(self.rng)
            noise = utilities.rand_arr(shape, gd)
            noisescalefac = np.sqrt(1. - np.abs(alpha**2))
            noiseFT = np.fft.fft2(noise)*powerlaw
            if self._phaseFT is None:
                self._phaseFT = noiseFT
            else:
                self._phaseFT = alpha*self._phaseFT + noiseFT*noisescalefac
            self.phase += np.fft.ifft2(self._phaseFT).real
        return self.phase

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()


def create_multilayer_arbase(size, scale, rate, r0, velocity, direction, alpha_mag):
    """
    Function to create the starting phase screen to be used for an
    autoregressive atmosphere model. A powerlaw scales random noise
    generated to make it look like Kolmogorov turbulence.  alpha is
    the autoregressive parameter to scale the current phase.

    @param size       Number of pixels across the screen
    @param scale      Pixel scale
    @param rate       A0 system rate (Hz)
    @param r0         Fried parameter (meters)
    @param velocity   Wind velocity (m/s)
    @param direction  Wind direction (galsim.Angle)
    @param alpha_mag  Magnitude of autoregressive parameter.  (1-alpha)
                      is the fraction of the phase from the prior time step
                      that is "forgotten" and replaced by Gaussian noise.
    """
    # Listify
    r0, velocity, direction, alpha_mag = map(
        lambda i: [i] if not hasattr(i, '__iter__') else i,
        (r0, velocity, direction, alpha_mag)
    )

    # Broadcast
    n_layers = max(map(len, [r0, velocity, direction, alpha_mag]))
    if n_layers > 1:
        r0, velocity, direction, alpha_mag = map(
            lambda i: [i[0]]*n_layers if len(i) == 1 else i,
            (r0, velocity, direction, alpha_mag)
        )

    if any(len(i) != n_layers for i in (r0, velocity, direction, alpha_mag)):
        raise ValueError("r0, velocity, direction, alpha_mag not broadcastable")

    # decompose velocities
    vx, vy = zip(*[v*d.sincos() for v, d in zip(velocity, direction)])

    screensize_meters = size*scale  # extent is given by aperture size and sampling
    deltaf = 1./screensize_meters   # spatial frequency delta

    # This is very similar to numpy.fftfreq, so we can probably use that, but for now
    # just copy over the original code from Srikar:
    # fx, fy = gg.generate_grids(n, scalefac=deltaf, freqshift=True)
    fx = np.zeros((size, size))
    for j in np.arange(size):
        fx[:, j] = j - (j > size/2)*size
    fx = fx * deltaf
    fy = fx.transpose()

    powerlaw = np.empty((n_layers, size, size), dtype=np.float64)
    alpha = np.empty((n_layers, size, size), dtype=np.complex128)
    for i, (r00, vx0, vy0, amag) in enumerate(zip(r0, vx, vy, alpha_mag)):
        pl = (2*np.pi/screensize_meters*np.sqrt(0.00058)*(r00**(-5.0/6.0)) *
              (fx*fx + fy*fy)**(-11.0/12.0) *
              size * np.sqrt(np.sqrt(2.0)))
        pl[0, 0] = 0.0
        powerlaw[i] = pl

        # make array for the alpha parameter and populate it
        # phase of alpha = -2pi(k*vx + l*vy)*T/Nd where T is sampling interval
        # N is WFS grid, d is subap size in meters = scale*m, k = 2pi*fx
        # fx, fy are k/Nd and l/Nd respectively
        alpha_phase = -(fx*vx0 + fy*vy0)/rate
        alpha[i] = amag * np.exp(2j*np.pi*alpha_phase)

    return powerlaw, alpha


class AtmosphericPSF(GSObject):
    """ Create an atmosphere PSF by summing over a phase cube in time steps.
    @param lam              Lambda (wavelength) in units of nanometers.  Must be supplied with
                            `diam`, and in this case, image scales (`scale`) should be specified in
                            units of `scale_unit`.
    @param r0               Fried parameter for each layer of turbulence in meters.
                            This parameter sets the amplitude of turbulence for each
                            layer. [Default: 0.2]
    @param lam_over_r0      Lambda / Fried parameter
    @param fwhm             Full width at half max (FWHM) of the PSF in the infinite
                            exposure limit in arcseconds. [Default: 0.8]
    @param alpha_mag        Magnitude of autoregressive parameter.  (1-alpha)
                            is the fraction of the phase from the prior time step
                            that is "forgotten" and replaced by Gaussian noise.
                            [Default: 0.999]
    @param exptime          Exposure time in seconds.
    @param time_step        Interval between PSF images in seconds. [Default: 0.03]
    @param velocity         Velocity magnitude of each phase screen layer in
                            meters / second. [Default: 0]
    @param direction        CCW relative to +x as galsim.Angle
                            [Default: 0*galsim.degrees]
    @param phase_cube       [Default: None]
    @param start_time       Start time in seconds for the simulation relative to the
                            beginning of the phase cube, if `phase_cube` is provided.
                            [Default: 0]
    @param stop_time        Stop time in seconds for the simulation relative to the
                            beginning of the phase cube, if `phase_cube` is provided.
                            [Default: None]
    @param interpolant      Either an Interpolant instance or a string indicating which interpolant
                            should be used.  Options are 'nearest', 'sinc', 'linear', 'cubic',
                            'quintic', or 'lanczosN' where N should be the integer order to use.
                            [default: galsim.Quintic()]
    @param oversampling     Optional oversampling factor for the InterpolatedImage. Setting
                            `oversampling < 1` will produce aliasing in the PSF (not good).
                            Usually `oversampling` should be somewhat larger than 1.  1.5 is
                            usually a safe choice.  [default: 1.5]
    @param flux             Total flux of the profile. [default: 1.]
    @param scale_unit       Units used to define the diffraction limit and draw images, if the user
                            has supplied a separate value for `lam` and `diam`.  Should be either a
                            galsim.AngleUnit, or a string that can be used to construct one (e.g.,
                            'arcsec', 'radians', etc.).
                            [default: galsim.arcsec]
    @param gsparams         An optional GSParams argument.  See the docstring for GSParams for
                            details. [default: None]
    """
    def __init__(self, lam=None, r0=0.2, lam_over_r0=None, fwhm=0.8,
                 alpha_mag=0.999, exptime=None, time_step=0.03, velocity=0,
                 direction=0*galsim.degrees, phase_generator=None, start_time=0.,
                 stop_time=None, interpolant=None, oversampling=1.5,
                 flux=1., scale_unit=galsim.arcsec, gsparams=None):
        import itertools
        nstep = int(np.ceil(exptime/time_step))
        if phase_generator is None:
            # Setup a new phase screen generator
            phase_generator = AtmosphericPhaseGenerator(
                time_step=time_step,
                screen_size=10., screen_scale=0.1, r0=r0, alpha_mag=alpha_mag,
                velocity=velocity, direction=direction)
        self.phase_generator = phase_generator

        pad = 2
        scale = pad / 10.0 * lam * galsim.radians / scale_unit
        # Generate PSFs for each time step
        screen = phase_generator.next()
        nx, ny = screen.shape
        im_grid = np.zeros((nx*pad, ny*pad), dtype=np.float64)
        for i, screen in itertools.izip(xrange(nstep), phase_generator):
            wf = np.zeros((nx*pad, ny*pad), dtype=np.float64)
            # The wavefront to use is exp(2 pi i screen)
            wf[(nx/2):(3*nx/2), (ny/2):(3*ny/2)] = np.exp(1j * screen)
            # Calculate the image array via FFT.
            # Copied from galsim.optics.psf method (hacky)
            ftwf = np.fft.ifft2(np.fft.ifftshift(wf))
            im = np.abs(ftwf)**2
            im = utilities.roll2d(im, (im.shape[0] / 2, im.shape[1] / 2))
            im *= (flux / (im.sum() * scale**2))
            # Add this PSF instance to stack to get the finite-exposure PSF
            im_grid += im

        out_im = galsim.InterpolatedImage(
            galsim.Image(im_grid.astype(np.float64), scale=scale))
        GSObject.__init__(self, out_im)
