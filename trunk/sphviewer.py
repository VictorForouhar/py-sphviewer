from scipy.spatial import cKDTree
import numpy as np
from scipy import weave
from scipy.weave import converters
import sys
import time

def import_code(filename):
	#naive function to import the .c files into scipy.weave
	string = ''
	fi = open(filename, 'r').readlines()
	for i in fi:
		string += i
	return string

def center_array(x):
	xmax = np.max(x)
	xmin = np.min(x)
	xmed = 0.5*(xmax+xmin)
	return (xmax-xmin),xmed

class scene(object):
	"""
	Main Class to render the particles
	"""
	def __init__(self, pos     = None, 
                           hsml    = None, 
                           rho     = None, 
                           nb      = 32, 
                           ac      = True, 
                           verbose = False):
#==========================
# particle parameters
		self.pos  = pos
		self.hsml = hsml
		self.rho  = rho
		self.nb   = nb
#==========================
#==========================
# Camera default parameters
		self.px      = 0.		# the camera is looking at (px,py,pz)
		self.py      = 0.		
		self.pz      = 0.	
		self.r       = 100.		# the camera is at distance r from (px,py,pz)
		self.theta   = 0.		# you can rotate the scene using theta and phi
		self.phi     = 0.		
		self.zoom    = 1.		# magnification of the camera.
		self.xsize   = 1000	        # x size of the image
		self.ysize   = 1000         	# y size of the image
#==========================
		self.verbose = verbose
		#If smoothing lenghts are not given we compute them.
		if(hsml == None): self.det_hsml()
		if ac == True: self.auto_camera()

	def auto_camera(self,distance_factor=0.65):
		"""
		Autocentering the camera params
		"""
		size_x, self.px = center_array(self.pos[0,:])
		size_y, self.py = center_array(self.pos[1,:])
		size_z, self.pz = center_array(self.pos[2,:])
		self.r = (distance_factor * 
			  np.sqrt(size_x**2+size_y**2+size_z**2))

	def det_hsml(self):
		"""
		Use det_hsml to compute the smoothing lenght and the density of your 
		particles. 
		"""	
		print 'Building 3DTree...'
		tree = cKDTree(self.pos.T)
		print 'Searching the ', self.nb, 'neighbors of each particle...'
		d, idx = tree.query(self.pos.T, k=self.nb)
		self.hsml = d[:,self.nb-1]
		if(self.rho == None):
			self.rho  = self.nb/(4./3.*np.pi*self.hsml**3)
		return

	def camera_params(self, px    = 0.,
                                py    = 0.,
                                pz    = 0., 
                                r     = 100.,
                                theta = 0.,
                                phi   = 0.,
                                zoom  = 1.,
                                xsize = 1000,
                                ysize = 1000,
                                par   = 0):
		"""
		Use camera_params to define the (px,py,pz) looking point of the camera,
		distance "r" of the observer, the angles "theta" and "phi" of camera, the 
		"zoom" and resolution of the image.
		"""
		self.px      = px		
		self.py      = py		
		self.pz      = pz	
		self.r       = r
		self.theta   = theta		
		self.phi     = phi
		self.zoom    = zoom	
		self.xsize   = xsize
		self.ysize   = ysize
		print '\n==============================='
		print '==== Parameters of camera: ===='
		print '(px,py,pz)           = ',     self.px,',',self.py,',',self.pz
		print 'r                    = ',     self.r
		print 'theta                = ',     self.theta
		print 'phi                  = ',     self.phi
		print 'zoom                 = ',     self.zoom
		print 'xsize                = ',     self.xsize
		print 'ysize                = ',     self.ysize
		print '================================'


	def make_scene(self, near = True,
                             lbox = None):
		#define near as False if you want to look at the scene from the infinity
		#lbox defines the physical lenght showed by the camera when near is False

		if( (near == False) & (lbox == None) ):
			print 'ERROR: If you selected near=False, you have to give some lbox value...'

		#factor to convert angles
		ac = np.pi/180.
		FOV   = 2.*np.abs(np.arctan(1./(self.zoom)))

		#camera watching from negative values
		self.xcam = -self.r*np.sin(self.phi*ac)*np.cos(self.theta*ac)
		self.ycam = +self.r*np.sin(self.theta*ac)
		self.zcam = -self.r*np.cos(self.phi*ac)*np.cos(self.theta*ac)
		
		if self.verbose:
			#we write the camera parameters for clarity
			print '\n==============================='
			print '==== Parameters of camera: ===='
			print '(px,py,pz)           = ',     self.px,',',self.py,',',self.pz
			print 'r                    = ',     self.r
			print 'theta                = ',     self.theta
			print 'phi                  = ',     self.phi
			print 'zoom                 = ',     self.zoom
			print 'xsize                = ',     self.xsize
			print 'ysize                = ',     self.ysize
			print '================================'
		# we first refer the positions to the camera point of view (px,py,pz) and 
		#then to its physic position (xcam, ycam, zcam). The stright line between
		# (px,py,pz) and (xcam,ycam,zcam) define the line of sight.
		if(near):
			x = self.pos[0,:]-(self.px+self.xcam)
			y = self.pos[1,:]-(self.py+self.ycam)
			z = self.pos[2,:]-(self.pz+self.zcam)

		#we need to take into account the real camera's FOV.
			xmax = self.zoom * np.tan(FOV/2.)
			xmin = - xmax
			ymax = 0.5*(xmax-xmin)*self.ysize/self.xsize	# in order to have symmetric y limits
			ymin = - ymax
			#when near is true we give the extent in angular units
			xfovmax =  FOV/2./ac
			xfovmin =  -FOV/2./ac
			yfovmax = 0.5*(xfovmax-xfovmin)*self.ysize/self.xsize
			yfovmin = -yfovmax
			extent = np.array([xfovmin,xfovmax,yfovmin,yfovmax])				
		else:
			x = self.pos[0,:]-(self.px)
			y = self.pos[1,:]-(self.py)
			z = self.pos[2,:]-(self.pz)

			xmax =  lbox/2.
			xmin = -lbox/2.
			ymax = 0.5*(xmax-xmin)*self.ysize/self.xsize	# in order to have symmetric y limits
			ymin = - ymax
			#when near is False we give the projected coordinates inside lbox 
			extent = np.array([xmin,xmax,ymin,ymax])

		if(self.phi   != 0.):				#we rotate around y axis
			xx_temp       = x*np.cos(self.phi*ac)-z*np.sin(self.phi*ac)
			z             = x*np.sin(self.phi*ac)+z*np.cos(self.phi*ac)
			x             = xx_temp
			xx_temp       = 0

		if(self.theta != 0.):			#we rotate around x axis
			yy_temp       = y*np.cos(self.theta*ac)+z*np.sin(self.theta*ac)
			z             = -y*np.sin(self.theta*ac)+z*np.cos(self.theta*ac)
			y             = yy_temp
			yy_temp       = 0

		# now we consider only particles in the line of sight inside de FOV of 
      # camera	
		if(near):
			kview = ( np.where( (z > 0.) & (np.abs(x) <= 
		                (np.abs(z)*np.tan(FOV/2.)) ) & (np.abs(y) <= 
		                (np.abs(z)*np.tan(FOV/2.)) ) )[0])

			x = x[kview]
			y = y[kview]
			z = z[kview]
			rho = self.rho[kview]
		else:
			kview = np.where( (x >= xmin) & (x <= xmax) & 
                                          (y >= ymin) & (y <= ymax) &
                                          ( np.abs(z) <= lbox/2 ) )[0]
			x = x[kview]
			y = y[kview]
			z = z[kview]
			rho = self.rho[kview]

		lbin = 2*xmax/self.xsize

		if self.verbose:
			print '-------------------------------------------------'
			print 'Making the smooth image'
			print 'xmin  =', xmin
			print 'xmax  =', xmax
			print 'ymin  =', ymin
			print 'ymax  =', ymax
			print 'xsize =', self.xsize
			print 'ysize =', self.ysize

		if(near):	
			x = ((x*self.zoom/z-xmin)/(xmax-xmin)*(self.xsize-1.)).astype(int)
			y = ((y*self.zoom/z-ymin)/(ymax-ymin)*(self.ysize-1.)).astype(int)
			t = (self.hsml[kview]*self.zoom/z/lbin).astype(int)
		else:
			x = ((x-xmin)/(xmax-xmin)*(self.xsize-1.)).astype(int)
			y = ((y-ymin)/(ymax-ymin)*(self.ysize-1.)).astype(int)
			t = (self.hsml[kview]/lbin).astype(int)
	
		n=int(len(x))

		dens = np.zeros([self.ysize,self.xsize],dtype=(np.float))

		# interpolation kernel
		extra_code = import_code('extra_code.c')
		# C code for making the images
		code       = import_code('c_code.c')

		binx = self.xsize
		biny = self.ysize

		start = time.time()
		weave.inline(code,['x',
                                   'y',
                                   'binx',
                                   'biny', 
                                   't',
                                   'lbin',
                                   'n',
                                   'rho',
                                   'dens'],
                                   support_code=extra_code,
                                   type_converters=converters.blitz,
                                   compiler='gcc', 
                                   extra_compile_args=[' -O3 -fopenmp'],
                                   extra_link_args=['-lgomp'])
		stop = time.time()

		if(self.verbose): print 'Elapsed time = ', stop-start
		return dens, np.array([self.xsize, self.ysize]), extent