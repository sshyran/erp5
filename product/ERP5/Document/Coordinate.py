##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
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

from Products.ERP5Type import Permissions, PropertySheet, Constraint, Interface
from Products.ERP5Type.Base import Base

class Coordinate(Base):
    """
        Coordinates is a mix-in class which is used to store elementary
        coordinates of an Entity (ex. Person, Organisation)

        UNKNOWN Coordinates are treated as a document
        with a subject (to find a given type of coordinate).

        Coordinates use a URL approach. Any coordinate can
        be rendered in a URL style. For example::

            - tel:+33(0)662057614

            - fax:+33(0)153010929

            - mailto:jp@nexedi.com

            - naf:722Z

            - smail://Nexedi/Jean-Paul Smets/943, av de la République/59700
                        Marcq-en-Baroeul/France

        Coordinates are stored as content within an Entity. Coordinate ids
        are generated as a combination of a so-called role (ex. shipping,
        billing, etc.) and a class string. This way, coordinates can
        be accessed as attributes of the containing Entity::

            - default_phone

            - default_fax

            - billing_address

            - shipping_address

        In order to be able to list all coordinates of an Entity,
        a list of Coordinate metatypes has to be defined and
        stored somewhere. (TODO)
        """
    # Declarative security (replaces __ac_permissions__)
    security = ClassSecurityInfo()

    ### Mix-in methods
    security.declareProtected( Permissions.View, 'view' )
    def view( self ):
        """
            Return the default view even if index_html is overridden.
        """
        return self()

    security.declareProtected( Permissions.View, 'SearchableText' )
    def SearchableText(self):
        """
            text for indexing
        """
        return "%s %s %s" % (self.title, self.description, self.asText())

    security.declareProtected( Permissions.View, 'asText' )
    def asText(self):
        """
            returns the coordinate as a text string
        """
        pass

    security.declareProtected( Permissions.ModifyPortalContent, 'fromText' )
    def fromText(self,coordinate_text):
        """
             modifies the coordinate according to the input text
             must be implemented by subclasses
        """
        pass

    security.declarePrivate( '_writeFromPUT' )
    def _writeFromPUT( self, body ):
        headers = {}
        headers, body = parseHeadersBody(body, headers)
        lines = string.split( body, '\n' )
        self.edit( lines[0] )
        headers['Format'] = self.COORDINATE_FORMAT
        new_subject = keywordsplitter(headers)
        headers['Subject'] = new_subject or self.Subject()
        haveheader = headers.has_key
        for key, value in self.getMetadataHeaders():
            if key != 'Format' and not haveheader(key):
                headers[key] = value

        self._editMetadata(title=headers['Title'],
                          subject=headers['Subject'],
                          description=headers['Description'],
                          contributors=headers['Contributors'],
                          effective_date=headers['Effective_date'],
                          expiration_date=headers['Expiration_date'],
                          format=headers['Format'],
                          language=headers['Language'],
                          rights=headers['Rights'],
                          )

    ## FTP handlers
    security.declareProtected( Permissions.ModifyPortalContent, 'PUT')
    def PUT(self, REQUEST, RESPONSE):
        """
            Handle HTTP / WebDAV / FTP PUT requests.
        """
        if not NoWL:
            self.dav__init(REQUEST, RESPONSE)
            self.dav__simpleifhandler(REQUEST, RESPONSE, refresh=1)
        body = REQUEST.get('BODY', '')
        try:
            self._writeFromPUT( body )
            RESPONSE.setStatus(204)
            return RESPONSE
        except ResourceLockedError, msg:
            get_transaction().abort()
            RESPONSE.setStatus(423)
            return RESPONSE

    security.declareProtected( Permissions.View, 'manage_FTPget' )
    def manage_FTPget(self):
        """
            Get the coordinate as text for WebDAV src / FTP download.
        """
        join = string.join
        lower = string.lower
        hdrlist = self.getMetadataHeaders()
        hdrtext = formatRFC822Headers( hdrlist )
        bodytext = '%s\n\n%s' % ( hdrtext, self.asText() )

        return bodytext

    security.declareProtected( Permissions.View, 'get_size' )
    def get_size( self ):
        """
            Used for FTP and apparently the ZMI now too
        """
        return len(self.manage_FTPget())
