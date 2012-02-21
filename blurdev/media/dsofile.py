##
#   \namespace  python.blurdev.media.dsofile
#
#   \remarks    This is a dso file parser used to read custom metadata for files that support the OLE data model originally created for Microsoft Word.
# 				Both 3dsMax and Softimage support this for .max, .scn, and .emdl.
#
# 				This class is a convience wrapper that uses win32com.client to communicate with a DLL.
# 				The 32bit version of the dll can be found at http://support.microsoft.com/kb/224351
# 				The 64bit version of the dll can be found at http://www.keysolutions.com/blogs/kenyee.nsf/d6plinks/KKYE-79KRU6
# 				Note: The 64bit version may have a few caveats that may affect you.
#
# 				To install the dll on a system call "regsvr32 dsofile.dll" from cmd.exe in the folder of the dll's I renamed the 64bit dll
# 				to dsofile64.dll
#
#   \author     mikeh@blur.com
#   \author     Blur Studio
#   \date       02/20/12
#

from win32com.client import Dispatch as _Dispatch
from blurdev.enum import enum as _enum


class DSOCustProperty:
    def __init__(self, property):
        self._property = property

    def name(self):
        return self._property.Name

    def setName(self, name):
        self._property.Name = name

    def setType(self, typ):
        self._property.Type = typ

    def setValue(self, value):
        self._property.Value = value

    def type(self):
        return self._property.Type

    def value(self):
        return self._property.Value


class DSOFile:
    PropertyTypes = _enum('String', 'Long', 'Double', 'Bool', 'Date')

    def __init__(self):
        self.dso = _Dispatch('DSOFile.OleDocumentProperties')

    # 		self.summaryProperties = None

    def __del__(self):
        # the dso must be closed if open, or it will lock the custom properties of the file
        self.dso.close()
        super(DSOFile, self).__del__()

    def addCustomProperty(self, key, value):
        r"""
            \remarks	Adds a custom property with the given key, value pair.
            \param		key		<str>
            \param		value	<Variant>
        """
        return self.dso.CustomProperties.Add(key, value)

    def close(self):
        self.dso.close()

    def customProperties(self):
        out = []
        for prop in self.dso.CustomProperties:
            out.append(DSOCustProperty(prop))
        return out

    def customProperty(self, key):
        r"""
            \remarks	Finds the key with the provided name and returns a custom Property. If the key is not found it returns None.
            \param		name	<str>
            \return		<DSOCustProperty>||<None>
        """
        for item in self.dso.CustomProperties:
            if item.Name == key:
                return DSOCustProperty(item)
        return None

    def customPropertyNames(self):
        out = []
        for item in self.dso.CustomProperties:
            out.append(item.Name)
        return out

    def open(self, filename):
        r"""
            \return		<bool>	returns true if the provided file supports dso.
        """
        self.dso.Open(filename)
        if self.dso.IsOleFile:
            # 			self.summaryProperties = DSOSummaryInformation(self.dso.SummaryProperties)
            return True
        self.close()
        return False

    def save(self):
        self.dso.save()


# This can be used to access the standard properties. Currently changes made with this do not show up in max's file properties dialog.
# class DSOSummaryInformation:
# 	def __init__(self, props):
# 		self.props = props
#
# 	def ApplicationName(self):
# 		return self.props.ApplicationName
#
# 	def author(self):
# 		return self.props.Author
#
# 	def CharacterCount(self):
# 		return self.props.CharacterCount
#
# 	def comments(self):
# 		return self.props.Comments
#
# 	def dateLastCreated(self):
# 		return self.props.DateCreated
#
# 	def dateLastPrinted(self):
# 		return self.props.DateLastPrinted
#
# 	def dateLastSaved(self):
# 		return self.props.DateLastSaved
#
# 	def documentSecurity(self):
# 		return self.props.DocumentSecurity
#
# 	def keywords(self):
# 		return self.props.Keywords
#
# 	def lastSavedBy(self):
# 		return self.props.LastSavedBy
#
# 	def pageCount(self):
# 		return self.props.PageCount
#
# 	def revisionNumber(self):
# 		return self.props.RevisionNumber
#
# 	def subject(self):
# 		return self.props.Subject
#
# 	def template(self):
# 		return self.props.Temlate
#
# 	def thumbnail(self):
# 		return self.props.Thumbnail
#
# 	def title(self):
# 		return self.props.Title
#
# 	def totalEditTime(self):
# 		return self.props.TotalEditTime
#
# 	def wordCount(self):
# 		return self.props.WordCount
#
# 	def setAuthor(self, value):
# 		self.props.Author = value
#
# 	def setComments(self, value):
# 		self.props.Comments = value
#
# 	def setKeywords(self, value):
# 		self.props.Keywords = value
#
# 	def setLastSavedBy(self, value):
# 		self.props.LastSavedBy = value
#
# 	def setSubject(self, value):
# 		self.props.Subject = value
#
# 	def setTitle(self, value):
# 		self.props.Title = value
