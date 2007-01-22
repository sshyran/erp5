##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
#
# Based on Photo by Ron Bickers
# Copyright (c) 2001 Logic Etc, Inc.  All rights reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from AccessControl import ClassSecurityInfo
from Acquisition import aq_base

from Products.CMFCore.WorkflowCore import WorkflowMethod
from Products.ERP5Type import Permissions, PropertySheet, Constraint, Interface
from Products.ERP5.Document.File import File
from OFS.Image import Image as OFSImage
from OFS.Image import getImageInfo
from OFS.content_types import guess_content_type
import string, time, sys
from cStringIO import StringIO

from zLOG import LOG

# XXX This should be move to preferences
defaultdisplays = {'thumbnail' : (128,128),
                   'xsmall'    : (200,200),
                   'small'     : (320,320),
                   'medium'    : (480,480),
                   'large'     : (768,768),
                   'xlarge'    : (1024,1024)
                  }

default_formats = ['jpg', 'jpeg', 'png', 'gif', 'pnm', 'ppm']

class Image(File, OFSImage):
  """
    An Image is a File which contains image data. It supports
    various conversions of format, size, resolution through
    imagemagick. imagemagick was preferred due to its ability
    to support PDF files (incl. Adobe Illustrator) which make
    it very useful in the context of a graphic design shop.

    Image inherits from XMLObject and can be synchronized
    accross multiple sites.

    Subcontent: Image can only contain role information.

    TODO:
    * extend Image to support more image file formats,
      including Xara Xtreme (http://www.xaraxtreme.org/)
    * include upgrade methods so that previous images
      in ERP5 get upgraded automatically to new class
  """
  # CMF Type Definition
  meta_type = 'ERP5 Image'
  portal_type = 'Image'
  isPortalContent = 1
  isRADContent = 1

  # Default attribute values
  width = 0
  height = 0

  # Declarative security
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)

  # Default Properties
  property_sheets = ( PropertySheet.Base
                    , PropertySheet.CategoryCore
                    , PropertySheet.DublinCore
                    , PropertySheet.Version
                    , PropertySheet.Reference
                    , PropertySheet.Document
                    , PropertySheet.Data
                    )

  #
  # Original photo attributes
  #

  def _update_image_info(self):
    """
      This method tries to determine the content type of an image and
      its geometry. It uses currently OFS.Image for this purpose.
      However, this method is known to be too simplistic.

      TODO:
      - use image magick or PIL
    """
    content_type, width, height = getImageInfo(self.data)
    self.height = height
    self.width = width
    self._setContentType(content_type)

  security.declareProtected(Permissions.AccessContentsInformation, 'getWidth')
  def getWidth(self):
    """
      Tries to get the width from the image data. 
    """
    if self.get_size() and not self.width: self._update_image_info()
    return self.width

  security.declareProtected(Permissions.AccessContentsInformation, 'getHeight')
  def getHeight(self):
    """
      Tries to get the height from the image data.
    """
    if self.get_size() and not self.height: self._update_image_info()
    return self.height

  security.declareProtected(Permissions.AccessContentsInformation, 'getContentType')
  def getContentType(self, format=''):
    """Original photo content_type."""
    if format == '':
      return self._baseGetContentType()
    else:
      return guess_content_type('myfile.' + format)[0]

  #
  # Photo display methods
  #

  security.declareProtected('View', 'tag')
  def tag(self, display=None, height=None, width=None, cookie=0,
                alt=None, css_class=None, format='', quality=75,
                resolution=None, **kw):
      """Return HTML img tag."""

      # Get cookie if display is not specified.
      if display is None:
          display = self.REQUEST.cookies.get('display', None)

      # display may be set from a cookie.
      if display is not None and defaultdisplays.has_key(display):
          if not self.hasConversion(display=display, format=format,
                                    quality=quality, resolution=resolution):
              # Generate photo on-the-fly
              self._makeDisplayPhoto(display, 1, format=format, quality=quality, resolution=resolution)
          mime, image = self.getConversion(display=display, format=format,
                                     quality=quality ,resolution=resolution)
          width, height = (image.width, image.height)
          # Set cookie for chosen size
          if cookie:
              self.REQUEST.RESPONSE.setCookie('display', display, path="/")
      else:
          # TODO: Add support for on-the-fly resize?
          height = self.getHeight()
          width = self.getWidth()

      if display:
          result = '<img src="%s?display=%s"' % (self.absolute_url(), display)
      else:
          result = '<img src="%s"' % (self.absolute_url())

      if alt is None:
          alt = getattr(self, 'title', '')
      if alt == '':
          alt = self.getId()
      result = '%s alt="%s"' % (result, html_quote(alt))

      if height:
          result = '%s height="%s"' % (result, height)

      if width:
          result = '%s width="%s"' % (result, width)

      if not 'border' in map(string.lower, kw.keys()):
          result = '%s border="0"' % (result)

      if css_class is not None:
          result = '%s class="%s"' % (result, css_class)

      for key in kw.keys():
          value = kw.get(key)
          result = '%s %s="%s"' % (result, key, value)

      result = '%s />' % (result)

      return result

  def __str__(self):
      return self.tag()

  security.declareProtected('Access contents information', 'displayIds')
  def displayIds(self, exclude=('thumbnail',)):
      """Return list of display Ids."""
      ids = defaultdisplays.keys()
      # Exclude specified displays
      if exclude:
          for id in exclude:
              if id in ids:
                  ids.remove(id)
      # Sort by desired photo surface area
      ids.sort(lambda x,y,d=self._displays: cmp(d[x][0]*d[x][1], d[y][0]*d[y][1]))
      return ids

  security.declareProtected('Access contents information', 'displayLinks')
  def displayLinks(self, exclude=('thumbnail',)):
      """Return list of HTML <a> tags for displays."""
      links = []
      for display in self.displayIds(exclude):
          links.append('<a href="%s?display=%s">%s</a>' % (self.REQUEST['URL'], display, display))
      return links

  security.declareProtected('Access contents information', 'displayMap')
  def displayMap(self, exclude=None, format='', quality=75, resolution=None):
      """Return list of displays with size info."""
      displays = []
      for id in self.displayIds(exclude):
          if self._isGenerated(id, format=format, quality=quality,resolution=resolution):
              photo_width = self._photos[(id,format)].width
              photo_height = self._photos[(id,format)].height
              bytes = self._photos[(id,format)]._size()
              age = self._photos[(id,format)]._age()
          else:
              (photo_width, photo_height, bytes, age) = (None, None, None, None)
          displays.append({'id': id,
                            'width': defaultdisplays[id][0],
                            'height': defaultdisplays[id][1],
                            'photo_width': photo_width,
                            'photo_height': photo_height,
                            'bytes': bytes,
                            'age': age
                            })
      return displays

  security.declareProtected('View', 'index_html')
  def index_html(self, REQUEST, RESPONSE, display=None, format='', quality=75, resolution=None):
      """Return the image data."""

      # Quick hack to maintain just enough compatibility for existing sites
      # Convert to new BTreeFolder2 based class
      if getattr(aq_base(self), '_count', None) is None:
        self._initBTrees()
      # Make sure old Image objects can still be accessed
      if not hasattr(aq_base(self), 'data') and hasattr(self, '_original'):
        self.data = self._original.data
        self.height = self._original.height
        self.width = self._original.width

      # display may be set from a cookie (?)
      if (display is not None or resolution is not None or quality != 75) and defaultdisplays.has_key(display):
          if not self.hasConversion(display=display, format=format,
                                    quality=quality,resolution=resolution):
              # Generate photo on-the-fly
              self._makeDisplayPhoto(display, 1, format=format, quality=quality,resolution=resolution)
          # Return resized image
          mime, image = self.getConversion(display=display, format=format,
                                     quality=quality ,resolution=resolution)
          return image.index_html(REQUEST, RESPONSE)

      # Return original image
      return OFSImage.index_html(self, REQUEST, RESPONSE)


  #
  # Photo processing
  #

  def _resize(self, display, width, height, quality=75, format='', resolution=None):
      """Resize and resample photo."""
      newimg = StringIO()

      if sys.platform == 'win32':
          from win32pipe import popen2
          from tempfile import mktemp
          newimg_path = mktemp(suffix=format)
          if resolution is None:
            imgin, imgout = popen2('convert -quality %s -geometry %sx%s - %s'
                                  % (quality, width, height, newimg_path), 'b')
          else:
            imgin, imgout = popen2('convert -density %sx%s -quality %s -geometry %sx%s - %s'
                                  % (resolution, resolution, quality, width, height, newimg_path), 'b')

      else:
          from popen2 import popen2
          import tempfile
          tempdir = tempfile.tempdir
          tempfile.tempdir = '/tmp'
          newimg_path = tempfile.mktemp(suffix='.' + format)
          tempfile.tempdir = tempdir
          if resolution is None:
            imgout, imgin = popen2('convert -quality %s -geometry %sx%s - %s'
                                  % (quality, width, height, newimg_path))
          else:
            LOG('Resolution',0,str(resolution))
            imgout, imgin = popen2('convert -density %sx%s -quality %s -geometry %sx%s - %s'
                                  % (resolution, resolution, quality, width, height, newimg_path))

      imgin.write(str(self.getData()))
      imgin.close()
      imgout.read()
      imgout.close()
      newimg_file = open(newimg_path, 'r')
      newimg.write(newimg_file.read())
      newimg_file.close()
      newimg.seek(0)
      return newimg

  def _getDisplayData(self, display, format='', quality=75, resolution=None):
      """Return raw photo data for given display."""
      (width, height) = defaultdisplays[display]
      if width == 0 and height == 0:
          width = self.getWidth()
          height = self.getHeight()
      (width, height) = self._getAspectRatioSize(width, height)
      return self._resize(display, width, height, quality, format=format, resolution=resolution)

  def _getDisplayPhoto(self, display, format='', quality=75, resolution=None):
      """Return photo object for given display."""
      try:
          base, ext = string.split(self.id, '.')
          id = base+'_'+display+'.'+ext
      except ValueError:
          id = self.id+'_'+display
      image = OFSImage(id, self.getTitle(), self._getDisplayData(display, format=format,
                                                                 quality=quality,resolution=resolution))
      return image

  def _makeDisplayPhoto(self, display, force=0, format='', quality=75, resolution=None):
      """Create given display."""
      if not self.hasConversion(display=display, format=format, quality=quality,resolution=resolution) or force:
          image = self._getDisplayPhoto(display, format=format, quality=quality, resolution=resolution)
          self.setConversion(image,  mime=image.content_type,
                                     display=display, format=format,
                                     quality=quality ,resolution=resolution)

  def _getAspectRatioSize(self, width, height):
      """Return proportional dimensions within desired size."""
      img_width, img_height = (self.getWidth(), self.getHeight())
      if height > img_height * width / img_width:
          height = img_height * width / img_width
      else:
          width =  img_width * height / img_height
      return (width, height)

  def _validImage(self):
      """At least see if it *might* be valid."""
      return self.getWidth() and self.getHeight() and self.getData() and self.getContentType()


  #
  # FTP/WebDAV support
  #

      #if hasattr(self, '_original'):
          ## Updating existing Photo
          #self._original.manage_upload(file, self.content_type())
          #if self._validImage():
              #self._makeDisplayPhotos()

  # Maybe needed
  #def manage_afterClone(self, item):

  # Maybe needed
  #def manage_afterAdd(self, item, container):
