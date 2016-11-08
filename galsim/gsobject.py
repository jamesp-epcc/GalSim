# Copyright (c) 2012-2016 by the GalSim developers team on GitHub
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
"""@file gsobject.py
Definitions for the class GSObject.

This file defines GSObject, the base class for all surface brightness profiles of astronomical
objects (galaxies, PSFs, pixel response), which defines the top-level interface to using all
of these classes.  The following other files include the implementations of various subclasses
which define specific surface brightness profiles:

    base.py defines simple objects like Gaussian, Moffat, Exponential, Sersic, etc.
    compound.py defines combinations of multiple GSObjects like Sum, Convolution, etc.
    inclinedexponential.py defines a 3D exponential disk at a specified inclination angle.
    interpolatedimage.py defines a surface brightness profile from an arbitrary image.
    phase_psf.py defines PSF profiles from the wavefront at the pupil plane.
    real.py defines RealGalaxy, which uses HST images of real observed galaxies.
    shapelet.py defines a profile from its shapelet (aka Gauss-Laguerre) decomposition.
    transform.py defines how other profiles can be sheared, rotated, shifted, etc.

All these classes have associated methods to (a) retrieve information (like the flux, half-light
radius, or intensity at a particular point); (b) carry out common operations, like shearing,
rescaling of flux or size, rotating, and shifting; and (c) actually make images of the surface
brightness profiles.
"""

import numpy as np

import galsim
from . import _galsim

class GSObject(object):
    """Base class for all GalSim classes that represent some kind of surface brightness profile.

    A GSObject is not intended to be constructed directly.  Normally, you would use whatever
    derived class is appropriate for the surface brightness profile you want:

        >>> gal = galsim.Sersic(n=4, half_light_radius=4.3)
        >>> psf = galsim.Moffat(beta=3, fwhm=2.85)
        >>> conv = galsim.Convolve([gal,psf])

    All of these classes are subclasses of GSObject, so you should see those docstrings for
    more details about how to construct the various profiles.  Here we discuss attributes and
    methods that are common to all GSObjects.

    GSObjects are always defined in sky coordinates.  So all sizes and other linear dimensions
    should be in terms of some kind of units on the sky, arcsec for instance.  Only later (when
    they are drawn) is the connection to pixel coordinates established via a pixel scale or WCS.
    (See the documentation for galsim.BaseWCS for more details about how to specify various kinds
    of world coordinate systems more complicated than a simple pixel scale.)

    For instance, if you eventually draw onto an image that has a pixel scale of 0.2 arcsec/pixel,
    then the normal thing to do would be to define your surface brightness profiles in terms of
    arcsec and then draw with `pixel_scale=0.2`.  However, while arcsec are the usual choice of
    units for the sky coordinates, if you wanted, you could instead define the sizes of all your
    galaxies and PSFs in terms of radians and then use `pixel_scale=0.2/206265` when you draw them.

    Transforming Methods
    --------------------

    The GSObject class uses an "immutable" design[1], so all methods that would potentially modify
    the object actually return a new object instead.  This uses pointers and such behind the
    scenes, so it all happens efficiently, but it makes using the objects a bit simpler, since
    you don't need to worry about some function changing your object behind your back.

    In all cases below, we just give an example usage.  See the docstrings for the methods for
    more details about how to use them.

        >>> obj = obj.shear(shear)      # Apply a shear to the object.
        >>> obj = obj.dilate(scale)     # Apply a flux-preserving dilation.
        >>> obj = obj.magnify(mu)       # Apply a surface-brightness-preserving magnification.
        >>> obj = obj.rotate(theta)     # Apply a rotation.
        >>> obj = obj.shift(dx,dy)      # Shft the object in real space.
        >>> obj = obj.transform(dudx,dudy,dvdx,dvdy)    # Apply a general jacobian transformation.
        >>> obj = obj.lens(g1,g2,mu)    # Apply both a lensing shear and magnification.
        >>> obj = obj.withFlux(flux)    # Set a new flux value.
        >>> obj = obj * ratio           # Scale the surface brightness profile by some factor.

    Access Methods
    --------------

    There are some access methods that are available for all GSObjects.  Again, see the docstrings
    for each method for more details.

        >>> flux = obj.getFlux()
        >>> centroid = obj.centroid()
        >>> f_xy = obj.xValue(x,y)
        >>> fk_xy = obj.kValue(kx,ky)
        >>> nyq = obj.nyquistScale()
        >>> stepk = obj.stepK()
        >>> maxk = obj.maxK()
        >>> hard = obj.hasHardEdges()
        >>> axisym = obj.isAxisymmetric()
        >>> analytic = obj.isAnalyticX()

    Most subclasses have additional methods that are available for values that are particular to
    that specific surface brightness profile.  e.g. `sigma = gauss.getSigma()`.  However, note
    that class-specific methods are not available after performing one of the above transforming
    operations.

        >>> gal = galsim.Gaussian(sigma=5)
        >>> gal = gal.shear(g1=0.2, g2=0.05)
        >>> sigma = gal.getSigma()              # This will raise an exception.

    It is however possible to access the original object that was transformed via the
    `original` attribute.

        >>> sigma = gal.original.getSigma()     # This works.

    No matter how many transformations are performed, the `original` attribute will contain the
    _original_ object (not necessarily the most recent ancestor).

    Drawing Methods
    ---------------

    The main thing to do with a GSObject once you have built it is to draw it onto an image.
    There are two methods that do this.  In both cases, there are lots of optional parameters.
    See the docstrings for these methods for more details.

        >>> image = obj.drawImage(...)
        >>> kimage = obj.drawKImage(...)

    Attributes
    ----------

    There two attributes that may be available for a GSObject.

        original    This was mentioned above as a way to access the original object that has
                    been transformed by one of the transforming methods.

        noise       Some types, like RealGalaxy, set this attribute to be the intrinsic noise that
                    is already inherent in the profile and will thus be present when you draw the
                    object.  The noise is propagated correctly through the various transforming
                    methods, as well as convolutions and flux rescalings.  Note that the `noise`
                    attribute can be set directly by users even for GSObjects that do not naturally
                    have one. The typical use for this attribute is to use it to whiten the noise in
                    the image after drawing.  See CorrelatedNoise for more details.

    GSParams
    --------

    All GSObject classes take an optional `gsparams` argument, so we document that feature here.
    For all documentation about the specific derived classes, please see the docstring for each
    one individually.

    The `gsparams` argument can be used to specify various numbers that govern the tradeoff between
    accuracy and speed for the calculations made in drawing a GSObject.  The numbers are
    encapsulated in a class called GSParams, and the user should make careful choices whenever they
    opt to deviate from the defaults.  For more details about the parameters and their default
    values, please see the docstring of the GSParams class (e.g. type `help(galsim.GSParams)`).

    For example, let's say you want to do something that requires an FFT larger than 4096 x 4096
    (and you have enough memory to handle it!).  Then you can create a new GSParams object with a
    larger `maximum_fft_size` and pass that to your GSObject on construction:

        >>> gal = galsim.Sersic(n=4, half_light_radius=4.3)
        >>> psf = galsim.Moffat(beta=3, fwhm=2.85)
        >>> conv = galsim.Convolve([gal,psf])
        >>> im = galsim.Image(1000,1000, scale=0.05)        # Note the very small pixel scale!
        >>> im = conv.drawImage(image=im)                   # This uses the default GSParams.
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "galsim/base.py", line 1236, in drawImage
            image.added_flux = prof.SBProfile.draw(imview.image)
        RuntimeError: SB Error: fourierDraw() requires an FFT that is too large, 6144
        If you can handle the large FFT, you may update gsparams.maximum_fft_size.
        >>> big_fft_params = galsim.GSParams(maximum_fft_size=10240)
        >>> conv = galsim.Convolve([gal,psf],gsparams=big_fft_params)
        >>> im = conv.drawImage(image=im)                   # Now it works (but is slow!)
        >>> im.write('high_res_sersic.fits')

    Note that for compound objects in compound.py, like Convolution or Sum, not all GSParams can be
    changed when the compound object is created.  In the example given here, it is possible to
    change parameters related to the drawing, but not the Fourier space parameters for the
    components that go into the Convolution.  To get better sampling in Fourier space, for example,
    the `gal` and/or `psf` should be created with `gsparams` that have a non-default value of
    `folding_threshold`.  This statement applies to the threshold and accuracy parameters.
    """
    _gsparams = { 'minimum_fft_size' : int,
                  'maximum_fft_size' : int,
                  'folding_threshold' : float,
                  'stepk_minimum_hlr' : float,
                  'maxk_threshold' : float,
                  'kvalue_accuracy' : float,
                  'xvalue_accuracy' : float,
                  'realspace_relerr' : float,
                  'realspace_abserr' : float,
                  'integration_relerr' : float,
                  'integration_abserr' : float,
                  'shoot_accuracy' : float,
                  'allowed_flux_variation' : float,
                  'range_division_for_extrema' : int,
                  'small_fraction_of_flux' : float
                }
    def __init__(self, obj):
        # This guarantees that all GSObjects have an SBProfile
        if isinstance(obj, GSObject):
            self.SBProfile = obj.SBProfile
            if hasattr(obj,'noise'):
                self.noise = obj.noise
        elif isinstance(obj, _galsim.SBProfile):
            self.SBProfile = obj
        else:
            raise TypeError("GSObject must be initialized with an SBProfile or another GSObject!")

    # a couple of definitions for using GSObjects as duck-typed ChromaticObjects
    @property
    def separable(self): return True
    @property
    def interpolated(self): return False
    @property
    def deinterpolated(self): return self
    @property
    def SED(self): return galsim.SED(self.flux, 'nm', '1')
    @property
    def spectral(self): return False
    @property
    def dimensionless(self): return True
    @property
    def wave_list(self): return np.array([], dtype=float)

    # Also need this method to duck-type as a ChromaticObject
    def evaluateAtWavelength(self, wave):
        """Return profile at a given wavelength.  For GSObject instances, this is just `self`.
        This allows GSObject instances to be duck-typed as ChromaticObject instances."""
        return self

    # Make op+ of two GSObjects work to return an Add object
    # Note: we don't define __iadd__ and similar.  Let python handle this automatically
    # to make obj += obj2 be equivalent to obj = obj + obj2.
    def __add__(self, other):
        return galsim.Add([self, other])

    # op- is unusual, but allowed.  It subtracts off one profile from another.
    def __sub__(self, other):
        return galsim.Add([self, (-1. * other)])

    # Make op* work to adjust the flux of an object
    def __mul__(self, other):
        """Scale the flux of the object by the given factor.

        obj * flux_ratio is equivalent to obj.withScaledFlux(flux_ratio)

        It creates a new object that has the same profile as the original, but with the
        surface brightness at every location scaled by the given amount.

        You can also multiply by an SED, which will create a ChromaticObject where the SED
        acts like a wavelength-dependent `flux_ratio`.
        """
        return self.withScaledFlux(other)

    def __rmul__(self, other):
        """Equivalent to obj * other"""
        return self.__mul__(other)

    # Likewise for op/
    def __div__(self, other):
        """Equivalent to obj * (1/other)"""
        return self * (1. / other)

    __truediv__ = __div__

    def __neg__(self):
        return -1. * self

    # Now define direct access to all SBProfile methods via calls to self.SBProfile.method_name()
    #
    def maxK(self):
        """Returns value of k beyond which aliasing can be neglected.
        """
        return self.SBProfile.maxK()

    def nyquistScale(self):
        """Returns Image pixel spacing that does not alias maxK.
        """
        return self.SBProfile.nyquistDx()

    def stepK(self):
        """Returns sampling in k space necessary to avoid folding of image in x space.
        """
        return self.SBProfile.stepK()

    def hasHardEdges(self):
        """Returns True if there are any hard edges in the profile, which would require very small k
        spacing when working in the Fourier domain.
        """
        return self.SBProfile.hasHardEdges()

    def isAxisymmetric(self):
        """Returns True if axially symmetric: affects efficiency of evaluation.
        """
        return self.SBProfile.isAxisymmetric()

    def isAnalyticX(self):
        """Returns True if real-space values can be determined immediately at any position without
        requiring a Discrete Fourier Transform.
        """
        return self.SBProfile.isAnalyticX()

    def isAnalyticK(self):
        """Returns True if k-space values can be determined immediately at any position without
        requiring a Discrete Fourier Transform.
        """
        return self.SBProfile.isAnalyticK()

    def centroid(self):
        """Returns the (x, y) centroid of an object as a Position.
        """
        return self.SBProfile.centroid()

    def getFlux(self):
        """Returns the flux of the object.
        """
        return self.SBProfile.getFlux()

    def maxSB(self):
        """Returns an estimate of the maximum surface brightness of the object.

        Some profiles will return the exact peak SB, typically equal to the value of
        obj.xValue(obj.centroid()).  However, not all profiles (e.g. Convolution) know how
        calculate this value without just drawing the image and checking what the maximum value is.
        Clearly, this would be inefficient, so in these cases, some kind of estimate is returned,
        which will generally be conservative on the high side.

        This routine is mainly used by the photon shooting process, where an overestimate of
        the maximum surface brightness is acceptable.

        Note, for negative-flux profiles, this will return the absolute value of the most negative
        surface brightness.  Technically, it is an estimate of the maximum deviation from zero,
        rather than the maximum value.  For most profiles, these are the same thing.
        """
        return self.SBProfile.maxSB()

    def getGSParams(self):
        """Returns the GSParams for the object.
        """
        return self.SBProfile.getGSParams()

    def calculateHLR(self, size=None, scale=None, centroid=None, flux_frac=0.5):
        """Returns the half-light radius of the object.

        If the profile has a half_light_radius attribute, it will just return that, but in the
        general case, we draw the profile and estimate the half-light radius directly.

        This function (by default at least) is only accurate to a few percent, typically.
        Possibly worse depending on the profile being measured.  If you care about a high
        precision estimate of the half-light radius, the accuracy can be improved using the
        optional parameter scale to change the pixel scale used to draw the profile.

        The default scale is half the Nyquist scale, which were found to produce results accurate
        to a few percent on our internal tests.  Using a smaller scale will be more accurate at
        the expense of speed.

        In addition, you can optionally specify the size of the image to draw. The default size is
        None, which means drawImage will choose a size designed to contain around 99.5% of the
        flux.  This is overkill for this calculation, so choosing a smaller size than this may
        speed up this calculation somewhat.

        Also, while the name of this function refers to the half-light radius, in fact it can also
        calculate radii that enclose other fractions of the light, according to the parameter
        `flux_frac`.  E.g. for r90, you would set flux_frac=0.90.

        The default scale should usually be acceptable for things like testing that a galaxy
        has a reasonable resolution, but they should not be trusted for very fine grain
        discriminations.

        @param size         If given, the stamp size to use for the drawn image. [default: None,
                            which will let drawImage choose the size automatically]
        @param scale        If given, the pixel scale to use for the drawn image. [default:
                            0.5 * self.nyquistScale()]
        @param centroid     The position to use for the centroid. [default: self.centroid()]
        @param flux_frac    The fraction of light to be enclosed by the returned radius.
                            [default: 0.5]

        @returns an estimate of the half-light radius in physical units
        """
        if hasattr(self, 'half_light_radius'):
            return self.half_light_radius

        if scale is None:
            scale = self.nyquistScale() * 0.5

        if centroid is None:
            centroid = self.centroid()

        # Draw the image.  Note: need a method that integrates over pixels to get flux right.
        # The offset is to make all the rsq values different to help the precision a bit.
        offset = galsim.PositionD(0.2, 0.33)
        im = self.drawImage(nx=size, ny=size, scale=scale, offset=offset, dtype=float)

        center = im.trueCenter() + offset + centroid/scale
        return im.calculateHLR(center=center, flux=self.flux, flux_frac=flux_frac)


    def calculateMomentRadius(self, size=None, scale=None, centroid=None, rtype='det'):
        """Returns an estimate of the radius based on unweighted second moments.

        The second moments are defined as:

        Q_ij = int( I(x,y) i j dx dy ) / int( I(x,y) dx dy )
        where i,j may be either x or y.

        If I(x,y) is a Gaussian, then T = Tr(Q) = Qxx + Qyy = 2 sigma^2.  Thus, one reasonable
        choice for a "radius" for an arbitrary profile is sqrt(T/2).

        In addition, det(Q) = sigma^4.  So another choice for an arbitrary profile is det(Q)^1/4.

        This routine can return either of these measures according to the value of the `rtype`
        parameter.  `rtype='trace'` will cause it to return sqrt(T/2).  `rtype='det'` will cause
        it to return det(Q)^1/4.  And `rtype='both'` will return a tuple with both values.

        Note that for the special case of a Gaussian profile, no calculation is necessary, and
        the `sigma` attribute will be used in both cases.  In the limit as scale->0, this
        function will return the same value, but because finite pixels are drawn, the results
        will not be precisely equal for real use cases.  The approximation being made is that
        the integral of I(x,y) i j dx dy over each pixel can be approximated as
        int(I(x,y) dx dy) * i_center * j_center.

        This function (by default at least) is only accurate to a few percent, typically.
        Possibly worse depending on the profile being measured.  If you care about a high
        precision estimate of the radius, the accuracy can be improved using the optional
        parameters size and scale to change the size and pixel scale used to draw the profile.

        The default is to use the the Nyquist scale for the pixel scale and let drawImage
        choose a size for the stamp that will enclose at least 99.5% of the flux.  These
        were found to produce results accurate to a few percent on our internal tests.
        Using a smaller scale and larger size will be more accurate at the expense of speed.

        The default parameters should usually be acceptable for things like testing that a galaxy
        has a reasonable resolution, but they should not be trusted for very fine grain
        discriminations.  For a more accurate estimate, see galsim.hsm.FindAdaptiveMom.

        @param size         If given, the stamp size to use for the drawn image. [default: None,
                            which will let drawImage choose the size automatically]
        @param scale        If given, the pixel scale to use for the drawn image. [default:
                            self.nyquistScale()]
        @param centroid     The position to use for the centroid. [default: self.centroid()]
        @param rtype        There are three options for this parameter:
                            - 'trace' means return sqrt(T/2)
                            - 'det' means return det(Q)^1/4
                            - 'both' means return both: (sqrt(T/2), det(Q)^1/4)
                            [default: 'det']

        @returns an estimate of the radius in physical units (or both estimates if rtype == 'both')
        """
        if rtype not in ['trace', 'det', 'both']:
            raise ValueError("rtype must be one of 'trace', 'det', or 'both'")

        if hasattr(self, 'sigma'):
            if rtype == 'both':
                return self.sigma, self.sigma
            else:
                return self.sigma

        if scale is None:
            scale = self.nyquistScale()

        if centroid is None:
            centroid = self.centroid()

        # Draw the image.  Note: need a method that integrates over pixels to get flux right.
        im = self.drawImage(nx=size, ny=size, scale=scale, dtype=float)

        center = im.trueCenter() + centroid/scale
        return im.calculateMomentRadius(center=center, flux=self.flux, rtype=rtype)


    def calculateFWHM(self, size=None, scale=None, centroid=None):
        """Returns the full-width half-maximum (FWHM) of the object.

        If the profile has a fwhm attribute, it will just return that, but in the general case,
        we draw the profile and estimate the FWHM directly.

        As with calculateHLR and calculateMomentRadius, this function optionally takes size and
        scale values to use for the image drawing.  The default is to use the the Nyquist scale
        for the pixel scale and let drawImage choose a size for the stamp that will enclose at
        least 99.5% of the flux.  These were found to produce results accurate to well below
        one percent on our internal tests, so it is unlikely that you will want to adjust
        them for accuracy.  However, using a smaller size than default could help speed up
        the calculation, since the default is usually much larger than is needed.

        @param size         If given, the stamp size to use for the drawn image. [default: None,
                            which will let drawImage choose the size automatically]
        @param scale        If given, the pixel scale to use for the drawn image. [default:
                            self.nyquistScale()]
        @param centroid     The position to use for the centroid. [default: self.centroid()]

        @returns an estimate of the full-width half-maximum in physical units
        """
        if hasattr(self, 'fwhm'):
            return self.fwhm

        if scale is None:
            scale = self.nyquistScale()

        if centroid is None:
            centroid = self.centroid()

        # Draw the image.  Note: draw with method='sb' here, since the fwhm is a property of the
        # raw surface brightness profile, not integrated over pixels.
        # The offset is to make all the rsq values different to help the precision a bit.
        offset = galsim.PositionD(0.2, 0.33)

        im = self.drawImage(nx=size, ny=size, scale=scale, offset=offset, method='sb', dtype=float)

        # Get the maximum value, assuming the maximum is at the centroid.
        if self.isAnalyticX():
            Imax = self.xValue(centroid)
        else:
            im1 = self.drawImage(nx=1, ny=1, scale=scale, method='sb', offset=-centroid/scale)
            Imax = im1(1,1)

        center = im.trueCenter() + offset + centroid/scale
        return im.calculateFWHM(center=center, Imax=Imax)


    @property
    def flux(self): return self.getFlux()
    @property
    def gsparams(self): return self.getGSParams()

    def xValue(self, *args, **kwargs):
        """Returns the value of the object at a chosen 2D position in real space.

        This function returns the surface brightness of the object at a particular position
        in real space.  The position argument may be provided as a PositionD or PositionI
        argument, or it may be given as x,y (either as a tuple or as two arguments).

        The object surface brightness profiles are typically defined in world coordinates, so
        the position here should be in world coordinates as well.

        Not all GSObject classes can use this method.  Classes like Convolution that require a
        Discrete Fourier Transform to determine the real space values will not do so for a single
        position.  Instead a RuntimeError will be raised.  The xValue() method is available if and
        only if `obj.isAnalyticX() == True`.

        Users who wish to use the xValue() method for an object that is the convolution of other
        profiles can do so by drawing the convolved profile into an image, using the image to
        initialize a new InterpolatedImage, and then using the xValue() method for that new object.

        @param position  The position at which you want the surface brightness of the object.

        @returns the surface brightness at that position.
        """
        pos = galsim.utilities.parse_pos_args(args,kwargs,'x','y')
        return self.SBProfile.xValue(pos)

    def kValue(self, *args, **kwargs):
        """Returns the value of the object at a chosen 2D position in k space.

        This function returns the amplitude of the fourier transform of the surface brightness
        profile at a given position in k space.  The position argument may be provided as a
        PositionD or PositionI argument, or it may be given as kx,ky (either as a tuple or as two
        arguments).

        Techinically, kValue() is available if and only if the given obj has `obj.isAnalyticK()
        == True`, but this is the case for all GSObjects currently, so that should never be an
        issue (unlike for xValue()).

        @param position  The position in k space at which you want the fourier amplitude.

        @returns the amplitude of the fourier transform at that position.
        """
        kpos = galsim.utilities.parse_pos_args(args,kwargs,'kx','ky')
        return self.SBProfile.kValue(kpos)

    def withFlux(self, flux):
        """Create a version of the current object with a different flux.

        This function is equivalent to `obj.withScaledFlux(flux / obj.getFlux())`.

        It creates a new object that has the same profile as the original, but with the
        surface brightness at every location rescaled such that the total flux will be
        the given value.  Note that if `flux` is an `SED`, the return value will be a
        `ChromaticObject` with specified SED.

        @param flux     The new flux for the object.

        @returns the object with the new flux
        """
        return self.withScaledFlux(flux / self.getFlux())

    def withScaledFlux(self, flux_ratio):
        """Create a version of the current object with the flux scaled by the given `flux_ratio`.

        This function is equivalent to `obj.withFlux(flux_ratio * obj.getFlux())`.  However, this
        function is the more efficient one, since it doesn't actually require the call to
        getFlux().  Indeed, withFlux() is implemented in terms of this one and getFlux().

        It creates a new object that has the same profile as the original, but with the
        surface brightness at every location scaled by the given amount.  If `flux_ratio` is an SED,
        then the returned object is a `ChromaticObject` with an SED multiplied by obj.getFlux().
        Note that in this case the `.flux` attribute of the GSObject being scaled gets interpreted
        as being dimensionless, instead of having its normal units of [photons/s/cm^2].  The
        photons/s/cm^2 units are (optionally) carried by the SED instead, or even left out entirely
        if the SED is dimensionless itself (see discussion in the ChromaticObject docstring).  The
        GSObject `flux` attribute *does* still contribute to the ChromaticObject normalization,
        though.  For example, the following are equivalent:

            >>> chrom_obj = gsobj.withScaledFlux(sed * 3.0)
            >>> chrom_obj2 = (gsobj * 3.0).withScaledFlux(sed)

        An equivalent, and usually simpler, way to effect this scaling is

            >>> obj = obj * flux_ratio

        @param flux_ratio   The ratio by which to rescale the flux of the object when creating a new
                            one.

        @returns the object with the new flux.
        """
        # Prohibit non-SED callable flux_ratio here as most likely an error.
        if hasattr(flux_ratio, '__call__') and not isinstance(flux_ratio, galsim.SED):
            raise TypeError('callable flux_ratio must be an SED.')

        new_obj = galsim.Transform(self, flux_ratio=flux_ratio)

        if not isinstance(new_obj, galsim.ChromaticObject) and hasattr(self, 'noise'):
            new_obj.noise = self.noise * flux_ratio**2
        return new_obj

    def expand(self, scale):
        """Expand the linear size of the profile by the given `scale` factor, while preserving
        surface brightness.

        e.g. `half_light_radius` <-- `half_light_radius * scale`

        This doesn't correspond to either of the normal operations one would typically want to do to
        a galaxy.  The functions dilate() and magnify() are the more typical usage.  But this
        function is conceptually simple.  It rescales the linear dimension of the profile, while
        preserving surface brightness.  As a result, the flux will necessarily change as well.

        See dilate() for a version that applies a linear scale factor while preserving flux.

        See magnify() for a version that applies a scale factor to the area while preserving surface
        brightness.

        @param scale    The factor by which to scale the linear dimension of the object.

        @returns the expanded object.
        """
        new_obj = galsim.Transform(self, jac=[scale, 0., 0., scale])

        if hasattr(self, 'noise'):
            new_obj.noise = self.noise.expand(scale)
        return new_obj

    def dilate(self, scale):
        """Dilate the linear size of the profile by the given `scale` factor, while preserving
        flux.

        e.g. `half_light_radius` <-- `half_light_radius * scale`

        See expand() and magnify() for versions that preserve surface brightness, and thus
        changes the flux.

        @param scale    The linear rescaling factor to apply.

        @returns the dilated object.
        """
        return self.expand(scale) * (1./scale**2)  # conserve flux

    def magnify(self, mu):
        """Create a version of the current object with a lensing magnification applied to it,
        scaling the area and flux by `mu` at fixed surface brightness.

        This process applies a lensing magnification mu, which scales the linear dimensions of the
        image by the factor sqrt(mu), i.e., `half_light_radius` <-- `half_light_radius * sqrt(mu)`
        while increasing the flux by a factor of mu.  Thus, magnify() preserves surface brightness.

        See dilate() for a version that applies a linear scale factor while preserving flux.

        See expand() for a version that applies a linear scale factor while preserving surface
        brightness.

        @param mu   The lensing magnification to apply.

        @returns the magnified object.
        """
        import math
        return self.expand(math.sqrt(mu))

    def shear(self, *args, **kwargs):
        """Create a version of the current object with an area-preserving shear applied to it.

        The arguments may be either a Shear instance or arguments to be used to initialize one.

        For more details about the allowed keyword arguments, see the documentation for Shear
        (for doxygen documentation, see galsim.shear.Shear).

        The shear() method precisely preserves the area.  To include a lensing distortion with
        the appropriate change in area, either use shear() with magnify(), or use lens(), which
        combines both operations.

        @param shear    The Shear to be applied. Or, as described above, you may instead supply
                        parameters do construct a shear directly.  eg. `obj.shear(g1=g1,g2=g2)`.

        @returns the sheared object.
        """
        if len(args) == 1:
            if kwargs:
                raise TypeError("Error, gave both unnamed and named arguments to GSObject.shear!")
            if not isinstance(args[0], galsim.Shear):
                raise TypeError("Error, unnamed argument to GSObject.shear is not a Shear!")
            shear = args[0]
        elif len(args) > 1:
            raise TypeError("Error, too many unnamed arguments to GSObject.shear!")
        else:
            shear = galsim.Shear(**kwargs)
        new_obj = galsim.Transform(self, jac=shear.getMatrix().ravel().tolist())

        if hasattr(self, 'noise'):
            new_obj.noise = self.noise.shear(shear)
        return new_obj

    def lens(self, g1, g2, mu):
        """Create a version of the current object with both a lensing shear and magnification
        applied to it.

        This GSObject method applies a lensing (reduced) shear and magnification.  The shear must be
        specified using the g1, g2 definition of shear (see Shear documentation for more details).
        This is the same definition as the outputs of the PowerSpectrum and NFWHalo classes, which
        compute shears according to some lensing power spectrum or lensing by an NFW dark matter
        halo.  The magnification determines the rescaling factor for the object area and flux,
        preserving surface brightness.

        @param g1       First component of lensing (reduced) shear to apply to the object.
        @param g2       Second component of lensing (reduced) shear to apply to the object.
        @param mu       Lensing magnification to apply to the object.  This is the factor by which
                        the solid angle subtended by the object is magnified, preserving surface
                        brightness.

        @returns the lensed object.
        """
        return self.shear(g1=g1, g2=g2).magnify(mu)

    def rotate(self, theta):
        """Rotate this object by an Angle `theta`.

        @param theta    Rotation angle (Angle object, +ve anticlockwise).

        @returns the rotated object.
        """
        if not isinstance(theta, galsim.Angle):
            raise TypeError("Input theta should be an Angle")
        s, c = theta.sincos()
        new_obj = galsim.Transform(self, jac=[c, -s, s, c])

        if hasattr(self, 'noise'):
            new_obj.noise = self.noise.rotate(theta)
        return new_obj

    def transform(self, dudx, dudy, dvdx, dvdy):
        """Create a version of the current object with an arbitrary Jacobian matrix transformation
        applied to it.

        This applies a Jacobian matrix to the coordinate system in which this object
        is defined.  It changes a profile defined in terms of (x,y) to one defined in
        terms of (u,v) where:

            u = dudx x + dudy y
            v = dvdx x + dvdy y

        That is, an arbitrary affine transform, but without the translation (which is
        easily effected via the shift() method).

        Note that this function is similar to expand in that it preserves surface brightness,
        not flux.  If you want to preserve flux, you should also do

            >>> prof *= 1./abs(dudx*dvdy - dudy*dvdx)

        @param dudx     du/dx, where (x,y) are the current coords, and (u,v) are the new coords.
        @param dudy     du/dy, where (x,y) are the current coords, and (u,v) are the new coords.
        @param dvdx     dv/dx, where (x,y) are the current coords, and (u,v) are the new coords.
        @param dvdy     dv/dy, where (x,y) are the current coords, and (u,v) are the new coords.

        @returns the transformed object
        """
        new_obj = galsim.Transform(self, jac=[dudx, dudy, dvdx, dvdy])
        if hasattr(self, 'noise'):
            new_obj.noise = self.noise.transform(dudx,dudy,dvdx,dvdy)
        return new_obj

    def shift(self, *args, **kwargs):
        """Create a version of the current object shifted by some amount in real space.

        After this call, the caller's type will be a GSObject.
        This means that if the caller was a derived type that had extra methods beyond
        those defined in GSObject (e.g. getSigma() for a Gaussian), then these methods
        are no longer available.

        Note: in addition to the dx,dy parameter names, you may also supply dx,dy as a tuple,
        or as a PositionD or PositionI object.

        The shift coordinates here are sky coordinates.  GSObjects are always defined in sky
        coordinates and only later (when they are drawn) is the connection to pixel coordinates
        established (via a pixel_scale or WCS).  So a shift of dx moves the object horizontally
        in the sky (e.g. west in the local tangent plane of the observation), and dy moves the
        object vertically (north in the local tangent plane).

        The units are typically arcsec, but we don't enforce that anywhere.  The units here just
        need to be consistent with the units used for any size values used by the GSObject.
        The connection of these units to the eventual image pixels is defined by either the
        `pixel_scale` or the `wcs` parameter of `drawImage`.

        Note: if you want to shift the object by a set number (or fraction) of pixels in the
        drawn image, you probably want to use the `offset` parameter of `drawImage` rather than
        this method.

        @param dx       Horizontal shift to apply.
        @param dy       Vertical shift to apply.

        @returns the shifted object.
        """
        offset = galsim.utilities.parse_pos_args(args, kwargs, 'dx', 'dy')
        new_obj = galsim.Transform(self, offset=offset)

        if hasattr(self,'noise'):
            new_obj.noise = self.noise
        return new_obj


    # Make sure the image is defined with the right size and wcs for drawImage()
    def _setup_image(self, image, nx, ny, bounds, add_to_image, dtype, odd=False, wmult=1.):
        # Check validity of nx,ny,bounds:
        if image is not None:
            if bounds is not None:
                raise ValueError("Cannot provide bounds if image is provided")
            if nx is not None or ny is not None:
                raise ValueError("Cannot provide nx,ny if image is provided")
            if dtype is not None and image.array.dtype != dtype:
                raise ValueError("Cannot specify dtype != image.array.dtype if image is provided")

        # Make image if necessary
        if image is None:
            # Can't add to image if none is provided.
            if add_to_image:
                raise ValueError("Cannot add_to_image if image is None")
            # Use bounds or nx,ny if provided
            if bounds is not None:
                if nx is not None or ny is not None:
                    raise ValueError("Cannot set both bounds and (nx, ny)")
                image = galsim.Image(bounds=bounds, dtype=dtype)
            elif nx is not None or ny is not None:
                if nx is None or ny is None:
                    raise ValueError("Must set either both or neither of nx, ny")
                image = galsim.Image(nx, ny, dtype=dtype)
            else:
                N = self.getGoodImageSize(1.0/wmult)
                if odd: N += 1
                image = galsim.Image(N, N, dtype=dtype)

        # Resize the given image if necessary
        elif not image.bounds.isDefined():
            # Can't add to image if need to resize
            if add_to_image:
                raise ValueError("Cannot add_to_image if image bounds are not defined")
            N = self.getGoodImageSize(1.0/wmult)
            if odd: N += 1
            bounds = galsim.BoundsI(1,N,1,N)
            image.resize(bounds)
            image.setZero()

        # Else use the given image as is
        else:
            # Clear the image if we are not adding to it.
            if not add_to_image:
                image.setZero()

        return image

    def _local_wcs(self, wcs, image, offset, use_true_center):
        # Get the local WCS at the location of the object.

        if wcs.isUniform():
            return wcs.local()
        elif image is None:
            # Should have already checked for this, but just to be safe, repeat the check here.
            raise ValueError("Cannot provide non-local wcs when image is None")
        elif not image.bounds.isDefined():
            raise ValueError("Cannot provide non-local wcs when image has undefined bounds")
        elif use_true_center:
            obj_cen = image.bounds.trueCenter()
        else:
            obj_cen = image.bounds.center()
            # Convert from PositionI to PositionD
            obj_cen = galsim.PositionD(obj_cen.x, obj_cen.y)
        # _parse_offset has already turned offset=None into PositionD(0,0), so it is safe to add.
        obj_cen += offset
        return wcs.local(image_pos=obj_cen)

    def _parse_offset(self, offset):
        if offset is None:
            return galsim.PositionD(0,0)
        else:
            if isinstance(offset, galsim.PositionD) or isinstance(offset, galsim.PositionI):
                return galsim.PositionD(offset.x, offset.y)
            else:
                # Let python raise the appropriate exception if this isn't valid.
                return galsim.PositionD(offset[0], offset[1])

    def _get_shape(self, image, nx, ny, bounds):
        if image is not None and image.bounds.isDefined():
            shape = image.array.shape
        elif nx is not None and ny is not None:
            shape = (ny,nx)
        elif bounds is not None and bounds.isDefined():
            shape = (bounds.ymax-bounds.ymin+1, bounds.xmax-bounds.xmin+1)
        else:
            shape = (0,0)
        return shape

    def _fix_center(self, shape, offset, use_true_center, reverse):
        # Note: this assumes self is in terms of image coordinates.
        if use_true_center:
            # For even-sized images, the SBProfile draw function centers the result in the
            # pixel just up and right of the real center.  So shift it back to make sure it really
            # draws in the center.
            # Also, remember that numpy's shape is ordered as [y,x]
            dx = offset.x
            dy = offset.y
            if shape[1] % 2 == 0: dx -= 0.5
            if shape[0] % 2 == 0: dy -= 0.5
            offset = galsim.PositionD(dx,dy)

        # For InterpolatedImage offsets, we apply the offset in the opposite direction.
        if reverse:
            offset = -offset

        if offset == galsim.PositionD(0,0):
            return self
        else:
            return self.shift(offset)

    def _determine_wcs(self, scale, wcs, image, default_wcs=None):
        # Determine the correct wcs given the input scale, wcs and image.
        if wcs is not None:
            if scale is not None:
                raise ValueError("Cannot provide both wcs and scale")
            if not wcs.isUniform():
                if image is None:
                    raise ValueError("Cannot provide non-local wcs when image is None")
                if not image.bounds.isDefined():
                    raise ValueError("Cannot provide non-local wcs when image has undefined bounds")
            if not isinstance(wcs, galsim.BaseWCS):
                raise TypeError("wcs must be a BaseWCS instance")
            if image is not None: image.wcs = None
        elif scale is not None:
            wcs = galsim.PixelScale(scale)
            if image is not None: image.wcs = None
        elif image is not None and image.wcs is not None:
            wcs = image.wcs

        # If the input scale <= 0, or wcs is still None at this point, then use the Nyquist scale:
        if wcs is None or (wcs.isPixelScale() and wcs.scale <= 0):
            if default_wcs is None:
                wcs = galsim.PixelScale(self.nyquistScale())
            else:
                wcs = default_wcs

        return wcs

    def drawImage(self, image=None, nx=None, ny=None, bounds=None, scale=None, wcs=None, dtype=None,
                  method='auto', area=1., exptime=1., gain=1., add_to_image=False,
                  use_true_center=True, offset=None, n_photons=0., rng=None, max_extra_noise=0.,
                  poisson_flux=None, setup_only=False, dx=None, wmult=1.):
        """Draws an Image of the object.

        The drawImage() method is used to draw an Image of the current object using one of several
        possible rendering methods (see below).  It can create a new Image or can draw onto an
        existing one if provided by the `image` parameter.  If the `image` is given, you can also
        optionally add to the given Image if `add_to_image = True`, but the default is to replace
        the current contents with new values.

        Note that if you provide an `image` parameter, it is the image onto which the profile
        will be drawn.  The provided image *will be modified*.  A reference to the same image
        is also returned to provide a parallel return behavior to when `image` is `None`
        (described above).

        This option is useful in practice because you may want to construct the image first and
        then draw onto it, perhaps multiple times. For example, you might be drawing onto a
        subimage of a larger image. Or you may want to draw different components of a complex
        profile separately.  In this case, the returned value is typically ignored.  For example:

                >>> im1 = bulge.drawImage()
                >>> im2 = disk.drawImage(image=im1, add_to_image=True)
                >>> assert im1 is im2

                >>> full_image = galsim.Image(2048, 2048, scale=pixel_scale)
                >>> b = galsim.BoundsI(x-32, x+32, y-32, y+32)
                >>> stamp = obj.drawImage(image = full_image[b])
                >>> assert (stamp.array == full_image[b].array).all()

        If drawImage() will be creating the image from scratch for you, then there are several ways
        to control the size of the new image.  If the `nx` and `ny` keywords are present, then an
        image with these numbers of pixels on a side will be created.  Similarly, if the `bounds`
        keyword is present, then an image with the specified bounds will be created.  Note that it
        is an error to provide an existing Image when also specifying `nx`, `ny`, or `bounds`. In
        the absence of `nx`, `ny`, and `bounds`, drawImage will decide a good size to use based on
        the size of the object being drawn.  Basically, it will try to use an area large enough to
        include at least 99.5% of the flux.  (Note: the value 0.995 is really `1 -
        folding_threshold`.  You can change the value of `folding_threshold` for any object via
        GSParams.  See `help(GSParams)` for more details.)  You can set the pixel scale of the
        constructed image with the `scale` parameter, or set a WCS function with `wcs`.  If you do
        not provide either `scale` or `wcs`, then drawImage() will default to using the Nyquist
        scale for the current object.  You can also set the data type used in the new Image with the
        `dtype` parameter that has the same options as for the Image constructor.

        There are several different possible methods drawImage() can use for rendering the image.
        This is set by the `method` parameter.  The options are:

            'auto'      This is the default, which will normally be equivalent to 'fft'.  However,
                        if the object being rendered is simple (no convolution) and has hard edges
                        (e.g. a Box or a truncated Moffat or Sersic), then it will switch to
                        'real_space', since that is often both faster and more accurate in these
                        cases (due to ringing in Fourier space).

            'fft'       The integration of the light within each pixel is mathematically equivalent
                        to convolving by the pixel profile (a Pixel object) and sampling the result
                        at the centers of the pixels.  This method will do that convolution using
                        a discrete Fourier transform.  Furthermore, if the object (or any component
                        of it) has been transformed via shear(), dilate(), etc., then these
                        transformations are done in Fourier space as well.

            'real_space'  This uses direct integrals (using the Gauss-Kronrod-Patterson algorithm)
                        in real space for the integration over the pixel response.  It is usually
                        slower than the 'fft' method, but if the profile has hard edges that cause
                        ringing in Fourier space, it can be faster and/or more accurate.  If you
                        use 'real_space' with something that is already a Convolution, then this
                        will revert to 'fft', since the double convolution that is required to also
                        handle the pixel response is far too slow to be practical using real-space
                        integrals.

            'phot'      This uses a technique called photon shooting to render the image.
                        Essentially, the object profile is taken as a probability distribution
                        from which a finite number of photons are "shot" onto the image.  Each
                        photon's flux gets added to whichever pixel the photon hits.  This process
                        automatically accounts for the integration of the light over the pixel
                        area, since all photons that hit any part of the pixel are counted.
                        Convolutions and transformations are simple geometric processes in this
                        framework.  However, there are two caveats with this method: (1) the
                        resulting image will have Poisson noise from the finite number of photons,
                        and (2) it is not available for all object types (notably anything that
                        includes a Deconvolution).

            'no_pixel'  Instead of integrating over the pixels, this method will sample the profile
                        at the centers of the pixels and multiply by the pixel area.  If there is
                        a convolution involved, the choice of whether this will use an FFT or
                        real-space calculation is governed by the `real_space` parameter of the
                        Convolution class.  This method is the appropriate choice if you are using
                        a PSF that already includes a convolution by the pixel response.  For
                        example, if you are using a PSF from an observed image of a star, then it
                        has already been convolved by the pixel, so you would not want to do so
                        again.  Note: The multiplication by the pixel area gets the flux
                        normalization right for the above use case.  cf. `method = 'sb'`.

            'sb'        This is a lot like 'no_pixel', except that the image values will simply be
                        the sampled object profile's surface brightness, not multiplied by the
                        pixel area.  This does not correspond to any real observing scenario, but
                        it could be useful if you want to view the surface brightness profile of an
                        object directly, without including the pixel integration.

        Normally, the flux of the object should be equal to the sum of all the pixel values in the
        image, less some small amount of flux that may fall off the edge of the image (assuming you
        don't use `method='sb'`).  However, you may optionally set a `gain` value, which converts
        between photons and ADU (so-called analog-to-digital units), the units of the pixel values
        in real images.  Normally, the gain of a CCD is in electrons/ADU, but in GalSim, we fold the
        quantum efficiency into the gain as well, so the units are photons/ADU.

        Another caveat is that, technically, flux is really in units of photons/cm^2/s, not photons.
        So if you want, you can keep track of this properly and provide an `area` and `exposure`
        time here. This detail is more important with chromatic objects where the SED is typically
        given in erg/cm^2/s/nm, so the exposure time and area are important details. With achromatic
        objects however, it is often more convenient to ignore these details and just consider the
        flux to be the total number of photons for this exposure, in which case, you would leave the
        area and exptime parameters at their default value of 1.

        The 'phot' method has a few extra parameters that adjust how it functions.  The total
        number of photons to shoot is normally calculated from the object's flux.  This flux is
        taken to be given in photons/cm^2/s, so for most simple profiles, this times area * exptime
        will equal the number of photons shot.  (See the discussion in Rowe et al, 2015, for why
        this might be modified for InterpolatedImage and related profiles.)  However, you can
        manually set a different number of photons with `n_photons`.  You can also set
        `max_extra_noise` to tell drawImage() to use fewer photons than normal (and so is faster)
        such that no more than that much extra noise is added to any pixel.  This is particularly
        useful if you will be subsequently adding sky noise, and you can thus tolerate more noise
        than the normal number of photons would give you, since using fewer photons is of course
        faster.  Finally, the default behavior is to have the total flux vary as a Poisson random
        variate, which is normally appropriate with photon shooting.  But you can turn this off with
        `poisson_flux=False`.  It also defaults to False if you set an explicit value for
        `n_photons`.

        The object will by default be drawn with its nominal center at the center location of the
        image.  There is thus a qualitative difference in the appearance of the rendered profile
        when drawn on even- and odd-sized images.  For a profile with a maximum at (0,0), this
        maximum will fall in the central pixel of an odd-sized image, but in the corner of the four
        central pixels of an even-sized image.  There are two parameters that can affect this
        behavior.  If you want the nominal center to always fall at the center of a pixel, you can
        use `use_true_center=False`.  This will put the object's center at the position
        `image.center()` which is an integer pixel value, and is not the true center of an
        even-sized image.  You can also arbitrarily offset the profile from the image center with
        the `offset` parameter to handle any sub-pixel dithering you want.

        On return, the image will have an attribute `added_flux`, which will be set to the total
        flux added to the image.  This may be useful as a sanity check that you have provided a
        large enough image to catch most of the flux.  For example:

            >>> obj.drawImage(image)
            >>> assert image.added_flux > 0.99 * obj.getFlux()

        The appropriate threshold will depend on your particular application, including what kind
        of profile the object has, how big your image is relative to the size of your object,
        whether you are keeping `poisson_flux=True`, etc.

        The following code snippet illustrates how `gain`, `exptime`, `area`, and `method` can all
        influence the relationship between the `flux` attribute of a `GSObject` and both the pixel
        values and `.added_flux` attribute of an `Image` drawn with `drawImage()`:

            >>> obj = galsim.Gaussian(fwhm=1)
            >>> obj.flux
            1.0
            >>> im = obj.drawImage()
            >>> im.added_flux
            0.9999630988657515
            >>> im.array.sum()
            0.99996305
            >>> im = obj.drawImage(exptime=10, area=10)
            >>> im.added_flux
            0.9999630988657525
            >>> im.array.sum()
            99.996315
            >>> im = obj.drawImage(exptime=10, area=10, method='sb', scale=0.5, nx=10, ny=10)
            >>> im.added_flux
            0.9999973790505298
            >>> im.array.sum()
            399.9989
            >>> im = obj.drawImage(exptime=10, area=10, gain=2)
            >>> im.added_flux
            0.9999630988657525
            >>> im.array.sum()
            49.998158

        Given the periodicity implicit in the use of FFTs, there can occasionally be artifacts due
        to wrapping at the edges, particularly for objects that are quite extended (e.g., due to
        the nature of the radial profile). See `help(galsim.GSParams)` for parameters that you can
        use to reduce the level of these artificats, in particular `folding_threshold` may be
        helpful if you see such artifacts in your images.

        @param image        If provided, this will be the image on which to draw the profile.
                            If `image` is None, then an automatically-sized Image will be created.
                            If `image` is given, but its bounds are undefined (e.g. if it was
                            constructed with `image = galsim.Image()`), then it will be resized
                            appropriately based on the profile's size [default: None].
        @param nx           If provided and `image` is None, use to set the x-direction size of the
                            image.  Must be accompanied by `ny`.
        @param ny           If provided and `image` is None, use to set the y-direction size of the
                            image.  Must be accompanied by `nx`.
        @param bounds       If provided and `image` is None, use to set the bounds of the image.
        @param scale        If provided, use this as the pixel scale for the image.
                            If `scale` is None and `image` is given, then take the provided
                            image's pixel scale.
                            If `scale` is None and `image` is None, then use the Nyquist scale.
                            If `scale <= 0` (regardless of `image`), then use the Nyquist scale.
                            If `scale > 0` and `image` is given, then override `image.scale` with
                            the value given as a keyword.
                            [default: None]
        @param wcs          If provided, use this as the wcs for the image (possibly overriding any
                            existing `image.wcs`).  At most one of `scale` or `wcs` may be provided.
                            [default: None]
        @param dtype        The data type to use for an automatically constructed image.  Only
                            valid if `image` is None. [default: None, which means to use
                            numpy.float32]
        @param method       Which method to use for rendering the image.  See discussion above
                            for the various options and what they do. [default: 'auto']
        @param area         Collecting area of telescope in cm^2.  [default: 1.]
        @param exptime      Exposure time in s.  [default: 1.]
        @param gain         The number of photons per ADU ("analog to digital units", the units of
                            the numbers output from a CCD).  [default: 1]
        @param add_to_image Whether to add flux to the existing image rather than clear out
                            anything in the image before drawing.
                            Note: This requires that `image` be provided and that it have defined
                            bounds. [default: False]
        @param use_true_center  Normally, the profile is drawn to be centered at the true center
                            of the image (using the function image.bounds.trueCenter()).
                            If you would rather use the integer center (given by
                            image.bounds.center()), set this to `False`.  [default: True]
        @param offset       The location in pixel coordinates at which to center the profile being
                            drawn relative to the center of the image (either the true center if
                            `use_true_center=True` or nominal center if `use_true_center=False`).
                            [default: None]
        @param n_photons    If provided, the number of photons to use for photon shooting.
                            If not provided (i.e. `n_photons = 0`), use as many photons as
                            necessary to result in an image with the correct Poisson shot
                            noise for the object's flux.  For positive definite profiles, this
                            is equivalent to `n_photons = flux`.  However, some profiles need
                            more than this because some of the shot photons are negative
                            (usually due to interpolants).
                            [default: 0]
        @param rng          If provided, a random number generator to use for photon shooting,
                            which may be any kind of BaseDeviate object.  If `rng` is None, one
                            will be automatically created, using the time as a seed.
                            [default: None]
        @param max_extra_noise  If provided, the allowed extra noise in each pixel when photon
                            shooting.  This is only relevant if `n_photons=0`, so the number of
                            photons is being automatically calculated.  In that case, if the image
                            noise is dominated by the sky background, then you can get away with
                            using fewer shot photons than the full `n_photons = flux`.  Essentially
                            each shot photon can have a `flux > 1`, which increases the noise in
                            each pixel.  The `max_extra_noise` parameter specifies how much extra
                            noise per pixel is allowed because of this approximation.  A typical
                            value for this might be `max_extra_noise = sky_level / 100` where
                            `sky_level` is the flux per pixel due to the sky.  Note that this uses
                            a "variance" definition of noise, not a "sigma" definition.
                            [default: 0.]
        @param poisson_flux Whether to allow total object flux scaling to vary according to
                            Poisson statistics for `n_photons` samples when photon shooting.
                            [default: True, unless `n_photons` is given, in which case the default
                            is False]
        @param setup_only   Don't actually draw anything on the image.  Just make sure the image
                            is set up correctly.  This is used internally by GalSim, but there
                            may be cases where the user will want the same functionality.
                            [default: False]

        @returns the drawn Image.
        """
        # Check for obsolete parameters
        if dx is not None and scale is None: # pragma: no cover
            from .deprecated import depr
            depr('dx', 1.1, 'scale')
            scale = dx
        if wmult != 1.: # pragma: no cover
            from .deprecated import depr
            depr('wmult', 1.5, 'GSParams(folding_threshold)',
                 'The old wmult parameter should not generally be required to get accurate FFT-'
                 'rendered images.  If you need larger FFT grids to prevent aliasing, you should '
                 'now use a gsparams object with a folding_threshold lower than the default 0.005.')

        # Check that image is sane
        if image is not None and not isinstance(image, galsim.Image):
            raise ValueError("image is not an Image instance")

        # Make sure (gain, area, exptime) have valid values:
        if gain <= 0.:
            raise ValueError("Invalid gain <= 0.")
        if area <= 0.:
            raise ValueError("Invalid area <= 0.")
        if exptime <= 0.:
            raise ValueError("Invalid exptime <= 0.")

        if method not in ['auto', 'fft', 'real_space', 'phot', 'no_pixel', 'sb']:
            raise ValueError("Invalid method name = %s"%method)

        # Check that the user isn't convolving by a Pixel already.  This is almost always an error.
        if method == 'auto' and isinstance(self, galsim.Convolution):
            if any([ isinstance(obj, galsim.Pixel) for obj in self.obj_list ]):
                import warnings
                warnings.warn(
                    "You called drawImage with `method='auto'` "
                    "for an object that includes convolution by a Pixel.  "
                    "This is probably an error.  Normally, you should let GalSim "
                    "handle the Pixel convolution for you.  If you want to handle the Pixel "
                    "convolution yourself, you can use method=no_pixel.  Or if you really meant "
                    "for your profile to include the Pixel and also have GalSim convolve by "
                    "an _additional_ Pixel, you can suppress this warning by using method=fft.")

        # Some parameters are only relevant for method == 'phot'
        if method != 'phot':
            if n_photons != 0.:
                raise ValueError("n_photons is only relevant for method='phot'")
            if rng is not None:
                raise ValueError("rng is only relevant for method='phot'")
            if max_extra_noise != 0.:
                raise ValueError("max_extra_noise is only relevant for method='phot'")
            if poisson_flux is not None:
                raise ValueError("poisson_flux is only relevant for method='phot'")

        # Figure out what wcs we are going to use.
        wcs = self._determine_wcs(scale, wcs, image)

        # Make sure offset is a PositionD
        offset = self._parse_offset(offset)

        # Get the local WCS, accounting for the offset correctly.
        local_wcs = self._local_wcs(wcs, image, offset, use_true_center)

        # Convert the profile in world coordinates to the profile in image coordinates:
        prof = local_wcs.toImage(self)

        # Account for area and exptime.
        flux_scale = area * exptime
        # For surface brightness normalization, also scale by the pixel area.
        if method == 'sb':
            flux_scale /= local_wcs.pixelArea()
        # Only do the gain here if not photon shooting, since need the number of photons to
        # reflect that actual photons, not ADU.
        if gain != 1 and method != 'phot':
            flux_scale /= gain

        prof *= flux_scale

        # If necessary, convolve by the pixel
        if method in ['auto', 'fft', 'real_space']:
            if method == 'auto':
                real_space = None
            elif method == 'fft':
                real_space = False
            else:
                real_space = True
            prof = galsim.Convolve(prof, galsim.Pixel(scale=1.0), real_space=real_space)

        # Apply the offset, and possibly fix the centering for even-sized images
        shape = prof._get_shape(image, nx, ny, bounds)
        prof = prof._fix_center(shape, offset, use_true_center, reverse=False)

        # Make sure image is setup correctly
        image = prof._setup_image(image, nx, ny, bounds, add_to_image, dtype, wmult=wmult)
        image.wcs = wcs

        if setup_only:
            image.added_flux = 0.
            return image

        # Making a view of the image lets us change the center without messing up the original.
        imview = image.view()
        imview.setCenter(0,0)
        imview.wcs = galsim.PixelScale(1.0)

        if method == 'phot':
            added_photons = prof.drawPhot(imview, n_photons, rng, max_extra_noise, poisson_flux,
                                          gain)
        elif prof.isAnalyticX():
            added_photons = prof.drawReal(imview)
        else:
            added_photons = prof.drawFFT(imview, wmult)

        image.added_flux = added_photons / flux_scale

        return image

    def drawReal(self, image):
        """
        Draw this profile into an Image by direct evaluation at the location of each pixel.

        This is usually called from the `drawImage` function, rather than called directly by the
        user.  In particular, the input image must be already set up with defined bounds with
        the center set to (0,0).  It also must have a pixel scale wcs.  The profile being
        drawn should have already been converted to image coordinates via

            >>> image_profile = original_wcs.toImage(original_profile)

        The image is not cleared out before drawing.  So this profile will be added to anything
        already on the input image.  This corresponds to `add_to_image=True` in the `drawImage`
        options.  If you don't want to add to the existing image, just call `image.setZero()`
        before calling `drawReal`.

        Note that the image produced by `drawReal` represents the profile sampled at the center
        of each pixel and then multiplied by the pixel area.  That is, the profile is NOT
        integrated over the area of the pixel.  If you want to render a profile integrated over
        the pixel, you can convolve with a Pixel first and draw that.

        @param image        The Image onto which to place the flux. [required]
                            Note: The flux will be added to any flux already on the image,
                            so this corresponds to the add_to_image=True option in drawImage.

        @returns The total flux drawin inside the image bounds.
        """
        return self.SBProfile.draw(image.image, image.scale)

    def getGoodImageSize(self, pixel_scale):
        """Return a good size to use for drawing this profile.

        The size will be large enough to cover most of the flux of the object.  Specifically,
        at least (1-gsparasm.folding_threshold) (i.e. 99.5% by default) of the flux should fall
        in the image.

        Also, the returned size is always an even number, which is usually desired in practice.
        Of course, if you prefer an odd-sized image, you can add 1 to the result.

        @param pixel_scale      The desired pixel scale of the image to be built.

        @returns N, a good (linear) size of an image on which to draw this object.
        """
        return self.SBProfile.getGoodImageSize(pixel_scale)

    def drawFFT(self, image, wmult=1.):
        """
        Draw this profile into an Image by direct evaluation at the location of each pixel.

        This is usually called from the `drawImage` function, rather than called directly by the
        user.  In particular, the input image must be already set up with defined bounds with
        the center set to (0,0).  It also must have a pixel scale of 1.0.  The profile being
        drawn should have already been converted to image coordinates via

            >>> image_profile = original_wcs.toImage(original_profile)

        The image is not cleared out before drawing.  So this profile will be added to anything
        already on the input image.  This corresponds to `add_to_image=True` in the `drawImage`
        options.  If you don't want to add to the existing image, just call `image.setZero()`
        before calling `drawFFT`.

        Note that the image produced by `drawFFT` represents the profile sampled at the center
        of each pixel and then multiplied by the pixel area.  That is, the profile is NOT
        integrated over the area of the pixel.  If you want to render a profile integrated over
        the pixel, you can convolve with a Pixel first and draw that.

        @param image        The Image onto which to place the flux. [required]
                            Note: The flux will be added to any flux already on the image,
                            so this corresponds to the add_to_image=True option in drawImage.

        @returns The total flux drawin inside the image bounds.
        """
        if wmult != 1.: # pragma: no cover
            from .deprecated import depr
            depr('wmult', 1.5, 'GSParams(folding_threshold)',
                 'The old wmult parameter should not generally be required to get accurate FFT-'
                 'rendered images.  If you need larger FFT grids to prevent aliasing, you should '
                 'now use a gsparams object with a folding_threshold lower than the default 0.005.')
            if type(wmult) != float:
                wmult = float(wmult)

        # Start with what this profile thinks a good size would be given the image's pixel scale.
        N = self.getGoodImageSize(image.scale/wmult)

        # We must make something big enough to cover the target image size:
        image_N = np.max(image.bounds.numpyShape())
        N = np.max((N, image_N))

        # Round up to a good size for making FFTs:
        N = image.good_fft_size(N)

        # Make sure we hit the minimum size specified in the gsparams.
        N = max(N, self.gsparams.minimum_fft_size)

        dk = 2.*np.pi / N

        if N*dk/2 > self.maxK():
            Nk = N
        else:
            # There will be aliasing.  Make a larger image and then wrap it.
            Nk = int(np.ceil(self.maxK()/dk)) * 2

        if Nk > self.gsparams.maximum_fft_size:
            raise RuntimeError(
                "drawFFT requires an FFT that is too large: %s."%Nk +
                "If you can handle the large FFT, you may update gsparams.maximum_fft_size.")

        # Draw the image in k space.
        bounds = galsim.BoundsI(0,Nk/2,-Nk/2,Nk/2)
        kimage = galsim.ImageC(bounds, scale=dk)
        self.SBProfile.drawK(kimage.image.view(), dk)

        # Wrap the full image to the size we want for the FT.
        # Even if N == Nk, this is useful to make this portion properly Hermitian in the
        # N/2 column and N/2 row.
        bwrap = galsim.BoundsI(0, N/2, -N/2, N/2-1)
        kimage_wrap = kimage.image.wrap(bwrap, True, False)

        # Perform the fourier transform.j
        real_image = kimage_wrap.inverse_fft(dk)

        # Add (a portion of) this to the original image.
        image.image += real_image.subImage(image.bounds)
        added_photons = real_image.subImage(image.bounds).array.sum()

        return added_photons

    def _calculate_nphotons(self, n_photons, poisson_flux, max_extra_noise, rng):
        """Calculate how many photons to shoot and what flux_ratio (called g) each one should
        have in order to produce an image with the right S/N and total flux.

        This routine is normally called by drawPhot.

        @returns n_photons, g
        """
        # For profiles that are positive definite, then N = flux. Easy.
        #
        # However, some profiles shoot some of their photons with negative flux. This means that
        # we need a few more photons to get the right S/N = sqrt(flux). Take eta to be the
        # fraction of shot photons that have negative flux.
        #
        # S^2 = (N+ - N-)^2 = (N+ + N- - 2N-)^2 = (Ntot - 2N-)^2 = Ntot^2(1 - 2 eta)^2
        # N^2 = Var(S) = (N+ + N-) = Ntot
        #
        # So flux = (S/N)^2 = Ntot (1-2eta)^2
        # Ntot = flux / (1-2eta)^2
        #
        # However, if each photon has a flux of 1, then S = (1-2eta) Ntot = flux / (1-2eta).
        # So in fact, each photon needs to carry a flux of g = 1-2eta to get the right
        # total flux.
        #
        # That's all the easy case. The trickier case is when we are sky-background dominated.
        # Then we can usually get away with fewer shot photons than the above.  In particular,
        # if the noise from the photon shooting is much less than the sky noise, then we can
        # use fewer shot photons and essentially have each photon have a flux > 1. This is ok
        # as long as the additional noise due to this approximation is "much less than" the
        # noise we'll be adding to the image for the sky noise.
        #
        # Let's still have Ntot photons, but now each with a flux of g. And let's look at the
        # noise we get in the brightest pixel that has a nominal total flux of Imax.
        #
        # The number of photons hitting this pixel will be Imax/flux * Ntot.
        # The variance of this number is the same thing (Poisson counting).
        # So the noise in that pixel is:
        #
        # N^2 = Imax/flux * Ntot * g^2
        #
        # And the signal in that pixel will be:
        #
        # S = Imax/flux * (N+ - N-) * g which has to equal Imax, so
        # g = flux / Ntot(1-2eta)
        # N^2 = Imax/Ntot * flux / (1-2eta)^2
        #
        # As expected, we see that lowering Ntot will increase the noise in that (and every
        # other) pixel.
        # The input max_extra_noise parameter is the maximum value of spurious noise we want
        # to allow.
        #
        # So setting N^2 = Imax + nu, we get
        #
        # Ntot = flux / (1-2eta)^2 / (1 + nu/Imax)
        # g = (1 - 2eta) * (1 + nu/Imax)
        #
        # Returns the total flux placed inside the image bounds by photon shooting.
        #

        flux = self.SBProfile.getFlux()
        posflux = self.SBProfile.getPositiveFlux()
        negflux = self.SBProfile.getNegativeFlux()
        eta = negflux / (posflux + negflux)
        eta_factor = 1.-2.*eta  # This is also the amount to scale each photon.
        mod_flux = flux/(eta_factor*eta_factor)

        # Use this for the factor by which to scale photon arrays.
        g = eta_factor

        # If requested, let the target flux value vary as a Poisson deviate
        if poisson_flux:
            # If we have both positive and negative photons, then the mix of these
            # already gives us some variation in the flux value from the variance
            # of how many are positive and how many are negative.
            # The number of negative photons varies as a binomial distribution.
            # <F-> = eta * Ntot * g
            # <F+> = (1-eta) * Ntot * g
            # <F+ - F-> = (1-2eta) * Ntot * g = flux
            # Var(F-) = eta * (1-eta) * Ntot * g^2
            # F+ = Ntot * g - F- is not an independent variable, so
            # Var(F+ - F-) = Var(Ntot*g - 2*F-)
            #              = 4 * Var(F-)
            #              = 4 * eta * (1-eta) * Ntot * g^2
            #              = 4 * eta * (1-eta) * flux
            # We want the variance to be equal to flux, so we need an extra:
            # delta Var = (1 - 4*eta + 4*eta^2) * flux
            #           = (1-2eta)^2 * flux
            mean = eta_factor*eta_factor * flux
            pd = galsim.PoissonDeviate(rng, mean)
            pd_val = pd() - mean + flux
            ratio = pd_val / flux
            g *= ratio
            mod_flux *= ratio

        if n_photons == 0.:
            n_photons = mod_flux
            if max_extra_noise > 0.:
                gfactor = 1. + max_extra_noise / self.SBProfile.maxSB()
                n_photons /= gfactor
                g *= gfactor

        # Make n_photons an integer.
        iN = int(n_photons + 0.5)

        if iN <= 0:  # pragma: no cover
            import warnings
            warnings.warn("Automatic n_photons calculation did not end up with positive N. " +
                          "(n_photons = %s)  No photons will be shot. "%n_photons +
                          "prof = %s  "%self +
                          "flux = %s  "%self.flux +
                          "poisson_flux = %s  "%poisson_flux +
                          "max_extra_noise = %s  "%max_extra_noise +
                          "g = %s  "%g)
            return 0, 1.

        return iN, g


    def drawPhot(self, image, n_photons=0, rng=None, max_extra_noise=None, poisson_flux=False,
                 gain=1.0):
        """
        Draw this profile into an Image by shooting photons.

        This is usually called from the `drawImage` function, rather than called directly by the
        user.  In particular, the input image must be already set up with defined bounds with
        the center set to (0,0).  It also must have a pixel scale of 1.0.  The profile being
        drawn should have already been converted to image coordinates via

            >>> image_profile = original_wcs.toImage(original_profile)

        The image is not cleared out before drawing.  So this profile will be added to anything
        already on the input image.  This corresponds to `add_to_image=True` in the `drawImage`
        options.  If you don't want to add to the existing image, just call `image.setZero()`
        before calling `drawPhot`.

        Note that the image produced by `drawPhot` represents the profile integrated over the
        area of each pixel.  This is equivalent to convolving the profile by a square `Pixel`
        profile and sampling the value at the center of each pixel.

        @param image        The Image onto which to place the flux. [required]
                            Note: The shot photons will be added to any flux already on the image,
                            so this corresponds to the add_to_image=True option in drawImage.
        @param n_photons    If provided, the number of photons to use for photon shooting.
                            If not provided (i.e. `n_photons = 0`), use as many photons as
                            necessary to result in an image with the correct Poisson shot
                            noise for the object's flux.  For positive definite profiles, this
                            is equivalent to `n_photons = flux`.  However, some profiles need
                            more than this because some of the shot photons are negative
                            (usually due to interpolants).  [default: 0]
        @param rng          If provided, a random number generator to use for photon shooting,
                            which may be any kind of BaseDeviate object.  If `rng` is None, one
                            will be automatically created, using the time as a seed.
                            [default: None]
        @param max_extra_noise  If provided, the allowed extra noise in each pixel when photon
                            shooting.  This is only relevant if `n_photons=0`, so the number of
                            photons is being automatically calculated.  In that case, if the image
                            noise is dominated by the sky background, then you can get away with
                            using fewer shot photons than the full `n_photons = flux`.  Essentially
                            each shot photon can have a `flux > 1`, which increases the noise in
                            each pixel.  The `max_extra_noise` parameter specifies how much extra
                            noise per pixel is allowed because of this approximation.  A typical
                            value for this might be `max_extra_noise = sky_level / 100` where
                            `sky_level` is the flux per pixel due to the sky.  Note that this uses
                            a "variance" definition of noise, not a "sigma" definition.
                            [default: 0.]
        @param poisson_flux Whether to allow total object flux scaling to vary according to
                            Poisson statistics for `n_photons` samples when photon shooting.
                            [default: True, unless `n_photons` is given, in which case the default
                            is False]
        @param gain         The number of photons per ADU ("analog to digital units", the units of
                            the numbers output from a CCD).  [default: 1.]

        @returns The total flux of photons that landed inside the image bounds.
        """
        # Make sure the type of n_photons is correct and has a valid value:
        if n_photons < 0.:
            raise ValueError("Invalid n_photons < 0.")

        if poisson_flux is None:
            if n_photons == 0.: poisson_flux = True
            else: poisson_flux = False

        # Check that either n_photons is set to something or flux is set to something
        if (n_photons == 0. and self.getFlux() == 1.
            and area == 1. and exptime == 1.): # pragma: no cover
            import warnings
            warnings.warn(
                    "Warning: drawImage for object with flux == 1, area == 1, and "
                    "exptime == 1, but n_photons == 0.  This will only shoot a single photon.")

        # Setup the rng if not provided one.
        if rng is None:
            ud = galsim.UniformDeviate()
        elif isinstance(rng, galsim.BaseDeviate):
            ud = galsim.UniformDeviate(rng)
        else:
            raise TypeError("The rng provided is not a BaseDeviate")

        # Make sure the image is set up to have unit pixel scale and centered at 0,0.
        if image.wcs != galsim.PixelScale(1.0):
            raise ValueError("drawPhot requires an image with scale=1.0")
        if image.center() != galsim.PositionI(0,0):
            raise ValueError("drawPhot requires an image centered at 0,0")

        Ntot, g = self._calculate_nphotons(n_photons, poisson_flux, max_extra_noise, ud)

        if gain != 1.:
            g /= gain

        # total flux falling inside image bounds, this will be returned on exit.
        added_flux = 0.

        # Don't do more than this at a time to keep the  memory usage reasonable.
        maxN = 100000

        # Nleft is the number of photons remaining to shoot.
        Nleft = Ntot
        while Nleft > 0:
            # Shoot at most maxN at a time
            thisN = min(maxN, Nleft)

            try:
                phot_array = self.shoot(thisN, ud)
            except RuntimeError:  # pragma: no cover
                # Give some extra explanation as a warning, then raise the original exception
                # so the traceback shows as much detail as possible.
                import warnings
                warnings.warn(
                    "Unable to draw this GSObject with photon shooting.  Perhaps it is a "+
                    "Deconvolve or is a compound including one or more Deconvolve objects.")
                raise

            phot_array.scaleFlux(g * thisN / Ntot)

            added_flux += phot_array.addTo(image.image)
            Nleft -= thisN

        return added_flux


    def shoot(self, N, ud):
        """Shoot photons into a PhotonArray."""
        return self.SBProfile.shoot(N, ud)


    def drawKImage(self, image=None, nx=None, ny=None, bounds=None, scale=None,
                   add_to_image=False, dk=None, wmult=1., re=None, im=None, dtype=None, gain=None):
        """Draws the k-space (complex) Image of the object, with bounds optionally set by input
        Image instance.

        Normalization is always such that image(0,0) = flux.  Unlike the real-space drawImage()
        function, the (0,0) point will always be one of the actual pixel values.  For even-sized
        images, it will be 1/2 pixel above and to the right of the true center of the image.

        Another difference from  drawImage() is that a wcs other than a simple pixel scale is not
        allowed.  There is no `wcs` parameter here, and if the images have a non-trivial wcs (and
        you don't override it with the `scale` parameter), a TypeError will be raised.

        Also, there is no convolution by a pixel.  This is just a direct image of the Fourier
        transform of the surface brightness profile.

        @param image        If provided, this will be the ImageC onto which to draw the k-space
                            image.  If `image` is None, then an automatically-sized image will be
                            created.  If is is given, but its bounds are undefined, then it
                            will be resized appropriately based on the profile's size.
                            [default: None]
        @param nx           If provided and `image` is None, use to set the x-direction size of the
                            image.  Must be accompanied by `ny`.
        @param ny           If provided and `image` is None, use to set the y-direction size of the
                            image.  Must be accompanied by `nx`.
        @param bounds       If provided and `image` is None, use to set the bounds of the image.
        @param scale        If provided, use this as the pixel scale, dk, for the images.
                            If `scale` is None and `image` is given, then take the provided
                            images' pixel scale (which must be equal).
                            If `scale` is None and `image` is None, then use the Nyquist scale.
                            If `scale <= 0` (regardless of `image`), then use the Nyquist scale.
                            [default: None]
        @param add_to_image Whether to add to the existing images rather than clear out
                            anything in the image before drawing.
                            Note: This requires that `image` be provided and that it has defined
                            bounds. [default: False]

        @returns an ImageC instance (created if necessary)
        """
        if isinstance(image,galsim.Image) and isinstance(nx,galsim.Image):
            # If the user calls drawK(re,im), then give the proper deprecation below.
            re = image
            im = nx
            image = None
            nx = None

        # Check for obsolete parameters
        if dk is not None and scale is None: # pragma: no cover
            from .deprecated import depr
            depr('dk', 1.1, 'scale')
            scale = dk
        if wmult != 1.: # pragma: no cover
            from .deprecated import depr
            depr('wmult', 1.5, 'GSParams(folding_threshold)',
                 'The old wmult parameter should not generally be required to get accurate FFT-'
                 'rendered images.  If you need larger FFT grids to prevent aliasing, you should '
                 'now use a gsparams object with a folding_threshold lower than the default 0.005.')
        if re is not None or im is not None: # pragma: no cover
            from .deprecated import depr
            depr('re,im', 1.5, 'image as a single complex ImageC',
                 'Warning: the input re, im images are being changed to have their arrays be '
                 'the real and imag parts of the output ImageC object.')
            if re is None or im is None:
                raise ValueError("Only one of re or im was provided.")
            if image is not None:
                raise ValueError("re and im were provided along with image")
            image = re + 1j * im
        if dtype is not None: # pragma: no cover
            from .deprecated import depr
            depr('dtype', 1.5, '', 'dtype of returned image will always be numpy.complex128')
        if gain is not None: # pragma: no cover
            from .deprecated import depr
            depr('gain', 1.5, ''
                 "The gain parameter doesn't really make sense for drawKImage.  If you had been "
                 "using it, you should now just divide the final image by gain instead.")

        # Make sure provided image is an ImageC
        if image is not None and image.array.dtype != np.complex128:
            raise ValueError("Provided image must be an ImageC (aka Image(..., dtype=complex))")

        # Possibly get the scale from image.
        if image is not None and scale is None:
            # Grab the scale to use from the image.
            # This will raise a TypeError if image.wcs is not a PixelScale
            scale = image.scale

        # The input scale (via scale or image.scale) is really a dk value, so call it that for
        # clarity here, since we also need the real-space pixel scale, which we will call dx.
        if scale is None or scale <= 0:
            dk = self.stepK()
        else:
            dk = float(scale)
        if image is not None and image.bounds.isDefined():
            dx = np.pi/( np.max(image.array.shape) // 2 * dk )
        elif scale is None or scale <= 0:
            dx = self.nyquistScale()
        else:
            # Then dk = scale, which implies that we need to have dx smaller than nyquistScale
            # by a factor of (dk/stepk)
            dx = self.nyquistScale() * dk / self.stepK()

        # If the profile needs to be constructed from scratch, the _setup_image function will
        # do that, but only if the profile is in image coordinates for the real space image.
        # So make that profile.
        real_prof = galsim.PixelScale(dx).toImage(self)
        if image is None: dtype = np.complex128
        image = real_prof._setup_image(image, nx, ny, bounds, add_to_image, np.complex128,
                                       odd=True, wmult=wmult)

        # Set the wcs of the images to use the dk scale size
        image.scale = dk

        if re is not None or im is not None: # pragma: no cover
            # Make sure the input re and im images get all the right attributes to match
            # the output image.
            # This is a hack that won't get all use cases right, but probably most of them.
            re._array = image._array.real
            im._array = image._array.imag
            b = image.bounds
            re.image = _galsim.ImageView[np.float64](re._array, b.xmin, b.ymin)
            im.image = _galsim.ImageView[np.float64](im._array, b.xmin, b.ymin)
            re.scale = image.scale
            im.scale = image.scale
            re.setOrigin(image.origin())
            im.setOrigin(image.origin())

        # Making views of the images lets us change the centers without messing up the originals.
        image.setCenter(0,0)

        self.SBProfile.drawK(image.image.view(), dk)

        if gain is not None:  # pragma: no cover
            image /= gain

        return image

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.SBProfile == other.SBProfile)

    def __ne__(self, other): return not self.__eq__(other)
    def __hash__(self): return hash(("galsim.GSObject", self.SBProfile))

# Pickling an SBProfile is a bit tricky, since it's a base class for lots of other classes.
# Normally, we'll know what the derived class is, so we can just use the pickle stuff that is
# appropriate for that.  But if we get a SBProfile back from say the getObj() method of
# SBTransform, then we won't know what class it should be.  So, in this case, we use the
# repr to do the pickling.  This isn't usually a great idea in general, but it provides a
# convenient way to get the SBProfile to be the correct type in this case.
# So, getstate just returns the repr string.  And setstate builds the right kind of object
# by essentially doing `self = eval(repr)`.
_galsim.SBProfile.__getstate__ = lambda self: self.serialize()
def SBProfile_setstate(self, state):
    import galsim
    # In case the serialization uses these:
    from numpy import array, int16, int32, float32, float64
    # The serialization of an SBProfile object should eval to the right thing.
    # We essentially want to do `self = eval(state)`.  But that doesn't work in python of course.
    # Se we break up the serialization into the class and the args, then call init with that.
    cls, args = state.split('(',1)
    args = args[:-1]  # Remove final paren
    args = eval(args)
    self.__class__ = eval(cls)
    self.__init__(*args)
_galsim.SBProfile.__setstate__ = SBProfile_setstate
# Quick and dirty.  Just check serializations are equal.
_galsim.SBProfile.__eq__ = lambda self, other: self.serialize() == other.serialize()
_galsim.SBProfile.__ne__ = lambda self, other: not self.__eq__(other)
_galsim.SBProfile.__hash__ = lambda self: hash(self.serialize())
