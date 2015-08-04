import numpy
from lsst.sims.coordUtils import raDecFromPixelCoordinates, observedFromICRS, \
                                 calculatePixelCoordinates
from lsst.afw.cameraGeom import PUPIL, PIXELS, TAN_PIXELS, FOCAL_PLANE
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.afw.image.utils as afwImageUtils
import lsst.daf.base as dafBase

__all__ = ["_nativeLonLatFromRaDec", "_raDecFromNativeLonLat",
           "nativeLonLatFromRaDec", "raDecFromNativeLonLat",
           "tanWcsFromDetector"]


def _nativeLonLatFromRaDec(ra, dec, raPointing, decPointing):
    """
    Convert the RA and Dec of a star into `native' longitude and latitude.

    Native longitude and latitude are defined as what RA and Dec would be
    if the celestial pole were at the location where the telescope is pointing.
    The coordinate basis axes for this system is achieved by taking the true
    coordinate basis axes and rotating them once about the z axis and once about
    the x axis (or, by rotating the vector pointing to the RA and Dec being
    transformed once about the x axis and once about the z axis).  These
    are the Euler rotations referred to in Section 2.3 of

    Calabretta and Greisen (2002), A&A 395, p. 1077

    @param [in] ra is the RA of the star being transformed in radians

    @param [in] dec is the Dec of the star being transformed in radians

    @param [in] raPointing is the RA at which the telescope is pointing
    in radians

    @param [in] decPointing is the Dec at which the telescope is pointing
    in radians

    @param [out] lonOut is the native longitude in radians

    @param [out] latOut is the native latitude in radians

    Note: while ra and dec can be numpy.arrays, raPointing and decPointing
    must be floats (you cannot transform for more than one pointing at once)
    """

    x = -1.0*numpy.cos(dec)*numpy.sin(ra)
    y = numpy.cos(dec)*numpy.cos(ra)
    z = numpy.sin(dec)

    alpha = decPointing - 0.5*numpy.pi
    beta = -1.0*raPointing

    ca=numpy.cos(alpha)
    sa=numpy.sin(alpha)
    cb=numpy.cos(beta)
    sb=numpy.sin(beta)

    v2 = numpy.dot(numpy.array([
                                [1.0, 0.0, 0.0],
                                [0.0, ca, sa],
                                [0.0, -1.0*sa, ca]
                                ]),
                   numpy.dot(numpy.array([[cb, -1.0*sb, 0.0],
                                          [sb, cb, 0.0],
                                          [0.0, 0.0, 1.0]
                                          ]), numpy.array([x,y,z])))

    cc = numpy.sqrt(v2[0]*v2[0]+v2[1]*v2[1])
    latOut = numpy.arctan2(v2[2], cc)

    _y = v2[1]/numpy.cos(latOut)
    _ra = numpy.arccos(_y)
    _x = -numpy.sin(_ra)

    if type(_ra) is numpy.float64:
        if numpy.isnan(_ra):
            lonOut = 0.0
        elif (numpy.abs(_x)>1.0e-9 and numpy.sign(_x)!=numpy.sign(v2[0])) \
             or (numpy.abs(_y)>1.0e-9 and numpy.sign(_y)!=numpy.sign(v2[1])):
            lonOut = 2.0*numpy.pi-_ra
        else:
            lonOut = _ra
    else:
        _lonOut = [2.0*numpy.pi-rr if (numpy.abs(xx)>1.0e-9 and numpy.sign(xx)!=numpy.sign(v2_0)) \
                                   or (numpy.abs(yy)>1.0e-9 and numpy.sign(yy)!=numpy.sign(v2_1)) \
                                   else rr \
                                   for rr, xx, yy, v2_0, v2_1 in zip(_ra, _x, _y, v2[0], v2[1])]

        lonOut = numpy.array([0.0 if numpy.isnan(ll) else ll for ll in _lonOut])

    return lonOut, latOut


def nativeLonLatFromRaDec(ra, dec, raPointing, decPointing):
    """
    Convert the RA and Dec of a star into `native' longitude and latitude.

    Native longitude and latitude are defined as what RA and Dec would be
    if the celestial pole were at the location where the telescope is pointing.
    The coordinate basis axes for this system is achieved by taking the true
    coordinate basis axes and rotating them once about the z axis and once about
    the x axis (or, by rotating the vector pointing to the RA and Dec being
    transformed once about the x axis and once about the z axis).  These
    are the Euler rotations referred to in Section 2.3 of

    Calabretta and Greisen (2002), A&A 395, p. 1077

    @param [in] ra is the RA of the star being transformed in degrees

    @param [in] dec is the Dec of the star being transformed in degrees

    @param [in] raPointing is the RA at which the telescope is pointing
    in degrees

    @param [in] decPointing is the Dec at which the telescope is pointing
    in degrees

    @param [out] lonOut is the native longitude in degrees

    @param [out] latOut is the native latitude in degrees

    Note: while ra and dec can be numpy.arrays, raPointing and decPointing
    must be floats (you cannot transform for more than one pointing at once)
    """

    lon, lat = _nativeLonLatFromRaDec(numpy.radians(ra), numpy.radians(dec),
                                      numpy.radians(raPointing),
                                      numpy.radians(decPointing))

    return numpy.degrees(lon), numpy.degrees(lat)


def _raDecFromNativeLonLat(lon, lat, raPointing, decPointing):
    """
    Transform a star's position in native longitude and latitude into
    RA and Dec.  See the doc string for _nativeLonLatFromRaDec for definitions
    of native longitude and latitude.

    @param [in] lon is the native longitude in radians

    @param [in] lat is the native latitude in radians

    @param [in] raPointing is the RA at which the telescope is pointing in
    radians

    @param [in] decPointing is the Dec at which the telescope is pointing
    in radians

    @param [out] raOut is the RA of the star in radians

    @param [in] decOut is the Dec of the star in radians

    Note: while lon and lat can be numpy.arrays, raPointing and decPointing
    must be floats (you cannot transform for more than one pointing at once)
    """

    x = -1.0*numpy.cos(lat)*numpy.sin(lon)
    y = numpy.cos(lat)*numpy.cos(lon)
    z = numpy.sin(lat)

    alpha = 0.5*numpy.pi - decPointing
    beta = raPointing

    ca=numpy.cos(alpha)
    sa=numpy.sin(alpha)
    cb=numpy.cos(beta)
    sb=numpy.sin(beta)

    v2 = numpy.dot(numpy.array([[cb, -1.0*sb, 0.0],
                                [sb, cb, 0.0],
                                [0.0, 0.0, 1.0]
                                ]),
                                numpy.dot(numpy.array([[1.0, 0.0, 0.0],
                                                       [0.0, ca, sa],
                                                       [0.0, -1.0*sa, ca]
                                ]),
                                numpy.array([x,y,z])))


    cc = numpy.sqrt(v2[0]*v2[0]+v2[1]*v2[1])
    decOut = numpy.arctan2(v2[2], cc)

    _y = v2[1]/numpy.cos(decOut)
    _ra = numpy.arccos(_y)
    _x = -numpy.sin(_ra)

    if type(_ra) is numpy.float64:
        if numpy.isnan(_ra):
            raOut = 0.0
        elif (numpy.abs(_x)>1.0e-9 and numpy.sign(_x)!=numpy.sign(v2[0])) \
             or (numpy.abs(_y)>1.0e-9 and numpy.sign(_y)!=numpy.sign(v2[1])):
            raOut = 2.0*numpy.pi-_ra
        else:
            raOut = _ra
    else:
        _raOut = [2.0*numpy.pi-rr if (numpy.abs(xx)>1.0e-9 and numpy.sign(xx)!=numpy.sign(v2_0)) \
                                  or (numpy.abs(yy)>1.0e-9 and numpy.sign(yy)!=numpy.sign(v2_1)) \
                                  else rr \
                                  for rr, xx, yy, v2_0, v2_1 in zip(_ra, _x, _y, v2[0], v2[1])]

        raOut = numpy.array([0.0 if numpy.isnan(rr) else rr for rr in _raOut])


    return raOut, decOut


def raDecFromNativeLonLat(lon, lat, raPointing, decPointing):
    """
    Transform a star's position in native longitude and latitude into
    RA and Dec.  See the doc string for nativeLonLatFromRaDec for definitions
    of native longitude and latitude.

    @param [in] lon is the native longitude in degrees

    @param [in] lat is the native latitude in degrees

    @param [in] raPointing is the RA at which the telescope is pointing in
    degrees

    @param [in] decPointing is the Dec at which the telescope is pointing
    in degrees

    @param [out] raOut is the RA of the star in degrees

    @param [in] decOut is the Dec of the star in degrees

    Note: while lon and lat can be numpy.arrays, raPointing and decPointing
    must be floats (you cannot transform for more than one pointing at once)
    """

    ra, dec = _raDecFromNativeLonLat(numpy.radians(lon),
                                     numpy.radians(lat),
                                     numpy.radians(raPointing),
                                     numpy.radians(decPointing))

    return numpy.degrees(ra), numpy.degrees(dec)

def _getTanPixelBounds(afwDetector, afwCamera):

    tanPixelSystem = afwDetector.makeCameraSys(TAN_PIXELS)
    xPixMin = None
    xPixMax = None
    yPixMin = None
    yPixMax = None
    cornerPointList = afwDetector.getCorners(FOCAL_PLANE)
    for cornerPoint in cornerPointList:
        cameraPoint = afwCamera.transform(
                           afwDetector.makeCameraPoint(cornerPoint, FOCAL_PLANE),
                           tanPixelSystem).getPoint()

        xx = cameraPoint.getX()
        yy = cameraPoint.getY()
        if xPixMin is None or xx<xPixMin:
            xPixMin = xx
        if xPixMax is None or xx>xPixMax:
            xPixMax = xx
        if yPixMin is None or yy<yPixMin:
            yPixMin = yy
        if yPixMax is None or yy>yPixMax:
            yPixMax = yy

    return xPixMin, xPixMax, yPixMin, yPixMax


def tanWcsFromDetector(afwDetector, afwCamera, obs_metadata, epoch):
    """
    Take an afw.cameraGeom detector and return a WCS which approximates
    the focal plane as perfectly flat (i.e. it ignores optical distortions
    that the telescope may impose on the image)

    @param [in] afwDetector is an instantiation of afw.cameraGeom's Detector
    class which characterizes the detector for which you wish to return th
    WCS

    @param [in] afwCamera is an instantiation of afw.cameraGeom's Camera
    class which characterizes the camera containing afwDetector

    @param [in] obs_metadata is an instantiation of ObservationMetaData
    characterizing the telescope's current pointing

    @param [in] epoch is the epoch in Julian years of the equinox against
    which RA and Dec are measured

    @param [out] tanWcs is an instantiation of afw.image's TanWcs class
    representing the WCS of the detector as if there were no optical
    distortions imposed by the telescope.
    """

    xTanPixMin, xTanPixMax, \
    yTanPixMin, yTanPixMax = _getTanPixelBounds(afwDetector, afwCamera)


    xPixList = []
    yPixList = []
    nameList = []

    #dx and dy are set somewhat heuristically
    #setting them eqal to 0.1(max-min) lead to errors
    #on the order of 0.7 arcsec in the WCS

    dx = 0.5*(xTanPixMax-xTanPixMin)
    dy = 0.5*(yTanPixMax-yTanPixMin)
    for xx in numpy.arange(xTanPixMin, xTanPixMax+0.5*dx, dx):
        for yy in numpy.arange(yTanPixMin, yTanPixMax+0.5*dx, dx):
            xPixList.append(xx)
            yPixList.append(yy)
            nameList.append(afwDetector.getName())


    raList, decList = raDecFromPixelCoordinates(xPixList, yPixList, nameList,
                                                camera=afwCamera,
                                                obs_metadata=obs_metadata,
                                                epoch=epoch,
                                                includeDistortion=False)

    raPointing, decPointing = observedFromICRS(numpy.array([obs_metadata._unrefractedRA]),
                                               numpy.array([obs_metadata._unrefractedDec]),
                                               obs_metadata=obs_metadata, epoch=epoch)

    crPix1, crPix2 = calculatePixelCoordinates(ra=raPointing, dec=decPointing,
                                               chipNames=[afwDetector.getName()], camera=afwCamera,
                                               obs_metadata=obs_metadata, epoch=epoch,
                                               includeDistortion=False)

    lonList, latList = _nativeLonLatFromRaDec(raList, decList, raPointing[0], decPointing[0])

    #convert from native longitude and latitude to intermediate world coordinates
    #according to equations (12), (13), (54) and (55) of
    #
    #Calabretta and Greisen (2002), A&A 395, p. 1077
    #
    radiusList = 180.0/(numpy.tan(latList)*numpy.pi)
    uList = radiusList*numpy.sin(lonList)
    vList = -radiusList*numpy.cos(lonList)

    delta_xList = xPixList - crPix1[0]
    delta_yList = yPixList - crPix2[0]

    bVector = numpy.array([
                          (delta_xList*uList).sum(),
                          (delta_yList*uList).sum(),
                          (delta_xList*vList).sum(),
                          (delta_yList*vList).sum()
                          ])

    offDiag = (delta_yList*delta_xList).sum()
    xsq = numpy.power(delta_xList,2).sum()
    ysq = numpy.power(delta_yList,2).sum()

    aMatrix = numpy.array([
                          [xsq, offDiag, 0.0, 0.0],
                          [offDiag, ysq, 0.0, 0.0],
                          [0.0, 0.0, xsq, offDiag],
                          [0.0, 0.0, offDiag, ysq]
                          ])

    coeffs = numpy.linalg.solve(aMatrix, bVector)

    crValPoint = afwGeom.Point2D(numpy.degrees(raPointing[0]), numpy.degrees(decPointing[0]))
    crPixPoint = afwGeom.Point2D(crPix1[0], crPix2[0])

    fitsHeader = dafBase.PropertyList()
    fitsHeader.set("RADECSYS", "ICRS")
    fitsHeader.set("EQUINOX", epoch)
    fitsHeader.set("CRVAL1", numpy.degrees(raPointing[0]))
    fitsHeader.set("CRVAL2", numpy.degrees(decPointing[0]))
    fitsHeader.set("CRPIX1", crPix1[0])
    fitsHeader.set("CRPIX2", crPix2[0])
    fitsHeader.set("CTYPE1", "RA---TAN")
    fitsHeader.set("CTYPE2", "DEC--TAN")
    fitsHeader.setDouble("CD1_1", coeffs[0])
    fitsHeader.setDouble("CD1_2", coeffs[1])
    fitsHeader.setDouble("CD2_1", coeffs[2])
    fitsHeader.setDouble("CD2_2", coeffs[3])
    tanWcs = afwImage.cast_TanWcs(afwImage.makeWcs(fitsHeader))

    return tanWcs


def tanSipWcsFromDetector(afwDetector, afwCamera, obs_metadata, epoch):

    size = afwDetector.getPixelSize()

    tanWcs = tanWcsFromDetector(afwDetector, afwCamera, obs_metadata, epoch)

    mockExposure = afwImage.Exposure(int(size.getX()), int(size.getY()))
    mockExposure.setWcs(tanWcs)
    mockExposure.setDetector(afwDetector)

    outWcs = afwImageUtils.getDistortedWcs(mockExposure.getInfo())

    return outWcs

