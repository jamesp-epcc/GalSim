# Copyright (c) 2012-2014 by the GalSim developers team on GitHub
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
"""Unit tests for the WFIRST module (galsim.wfirst)
"""

import numpy as np

from galsim_test_helpers import *

try:
    import galsim
    import galsim.wfirst
except ImportError:
    import os
    import sys
    path, filename = os.path.split(__file__)
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

# The dict below is just a subset of a dict from test_wcs.py, which we'll use to test our ability to
# import WCSTools to use the WFIRST WCS software.
references = {
    'TAN' : ('1904-66_TAN.fits' ,
            [ ('193930.753119', '-634259.217527', 117, 178, 13.43628),
              ('181918.652839', '-634903.833411', 153, 35, 11.44438) ] ),
}
ref_dir = 'fits_files'

def test_wfirst_wcs():
    """Test the WFIRST WCS routines against those from software provided by WFIRST project office.
    """
    import time
    t1 = time.time()

    # The standard against which we will compare is the output of some software provided by Jeff
    # Kruk.  The files used here were generated by Rachel on her Macbook using the script in
    # wfirst_files/make_standards.sh, and none of the parameters below can be changed without
    # modifying and rerunning that script.  We use 4 sky positions and rotation angles (2 defined
    # using the focal plane array, 2 using the observatory coordinates), and in each case, use a
    # different SCA for our tests.  We will simply read in the stored WCS and generate new ones, and
    # check that they have the right value of SCA center and pixel scale at the center, and that if
    # we offset by 500 pixels in some direction that gives the same sky position in each case.
    ra_test = [127., 307.4, -61.52, 0.0]
    dec_test = [-70., 50., 22.7, 0.0]
    pa_test = [160., 79., 23.4, -3.1]
    sca_test = [2, 13, 7, 18]
    pa_is_fpa_test = [True, False, True, False]

    dist_arcsec = []
    dist_2_arcsec = []
    pix_area_ratio = []
    for i_test in range(len(ra_test)):
        # Make the WCS for this test.
        try:
            all_gs_wcs = galsim.wfirst.getWCS(pa_test[i_test]*galsim.degrees,
                                              ra=ra_test[i_test]*galsim.degrees,
                                              dec=dec_test[i_test]*galsim.degrees,
                                              PA_is_FPA=pa_is_fpa_test[i_test])
        except ImportError:
            print "Cannot find any software to read the WFIRST WCS.  Skipping this test."
            return
        # Read in reference.
        test_file = 'test%d_sca_%02d.fits'%(i_test+1, sca_test[i_test])
        ref_wcs = galsim.FitsWCS(os.path.join('wfirst_files',test_file))

        gs_wcs = all_gs_wcs[sca_test[i_test]]

        # Check center position:
        im_cent_pos = galsim.PositionD(galsim.wfirst.n_pix/2., galsim.wfirst.n_pix/2)
        ref_cent_pos = ref_wcs.toWorld(im_cent_pos)
        gs_cent_pos = gs_wcs.toWorld(im_cent_pos)
        dist_arcsec.append(ref_cent_pos.distanceTo(gs_cent_pos) / galsim.arcsec)

        # Check pixel area
        rat = ref_wcs.pixelArea(image_pos=im_cent_pos)/gs_wcs.pixelArea(image_pos=im_cent_pos)
        pix_area_ratio.append(rat-1.)

        # Check another position, just in case rotations are messed up.
        im_other_pos = galsim.PositionD(im_cent_pos.x+500., im_cent_pos.y)
        ref_other_pos = ref_wcs.toWorld(im_other_pos)
        gs_other_pos = gs_wcs.toWorld(im_other_pos)
        dist_2_arcsec.append(ref_other_pos.distanceTo(gs_other_pos) / galsim.arcsec)

    np.testing.assert_array_less(
        np.array(dist_arcsec),
        np.ones(len(ra_test))*galsim.wfirst.pixel_scale/100, 
        err_msg='For at least one WCS, center offset from reference was > 0.01(pixel scale).')
    np.testing.assert_array_less(
        np.array(dist_2_arcsec),
        np.ones(len(ra_test))*galsim.wfirst.pixel_scale/100, 
        err_msg='For at least one WCS, other offset from reference was > 0.01(pixel scale).')
    np.testing.assert_array_less(
        np.array(pix_area_ratio),
        np.ones(len(ra_test))*0.0001,
        err_msg='For at least one WCS, pixel areas differ from reference by >0.01%.')

    t2 = time.time()
    print 'time for %s = %.2f'%(funcname(),t2-t1)

if __name__ == "__main__":
    test_wfirst_wcs()
