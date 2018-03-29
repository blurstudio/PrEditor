##
#   :namespace  python.blurdev.scripts.reduceTools
#
#   :remarks    Scripts to convert the existing treegrunt code structure to the new flat structure.
# |				reduceTools.reduceCode(path)
#
#   :author     mikeh@blur.com
#   :author     Blur Studio
#   :date       07/12/12
#

from __future__ import print_function
import os, glob, re
from blurdev.XML import XMLDocument

try:
    import pysvn
except:
    pysvn = None


def reduceCode(rootPath):
    """ Master function to flatten the treegrunt structure """
    for folder in os.listdir(rootPath):
        if folder != '.svn':
            path = os.path.join(rootPath, folder)
            reducePath(path, rootPath, rootPath)


def reducePath(path, rootPath, dest=None):
    """
        :remarks	Process recursively the contents of a folder and svn move it to the destination.
        :param		path		<str>			The folder to process.
        :param		rootPath	<str>			Start building the category id from this folder.
        :param		dest		<str>||None		If provided it and pysvn is installed it will svn move all tools into this directory.
    """

    """
        Process recursively a folder """
    path = os.path.abspath(path)
    print('Processing Path:', end='')
    rootPath = os.path.abspath(rootPath)
    common = os.path.commonprefix([path, rootPath])
    if os.path.isdir(path):
        fileNames = glob.glob(path + '/*/__meta__.xml')
        for file in fileNames:
            print('	FileName:', file)
            # update the xml
            doc = XMLDocument()
            doc.load(file)
            root = doc.root()
            setValueForNode(
                root,
                'displayName',
                splitOnCaps(os.path.normpath(file).split(os.path.sep)[-2]),
            )
            print("	Name:", splitOnCaps(os.path.normpath(file).split(os.path.sep)[-2]))
            setValueForNode(root, 'category', pathToAddress(path, common))
            print("	Group", pathToAddress(path, common))
            doc.save(file)
            # Svn Move the folder to the destination
            if dest and pysvn:
                client = pysvn.Client()
                src = os.path.split(file)[0]
                print('	Src:', src)
                d = os.path.join(dest, os.path.split(src)[1])
                print('	Dest:', d)
                client.move(src, d)
        for dir in os.listdir(path):
            folder = os.path.join(path, dir)
            if dir != '.svn' and os.path.isdir(folder):
                reducePath(folder, rootPath, dest)


def setValueForNode(node, name, value):
    out = node.findChild(name)
    if not out:
        out = node.addNode(name)
    out.setValue(value)
    return out


def splitOnCaps(input):
    input = input.replace('_', ' ')
    input = re.sub(
        r'([a-z](?=[A-Z])|[A-Z](?=[A-Z][a-z])|[\d\.]+(?=[A-Z]))', r'\1 ', input
    )
    return re.sub(r'([\d\.]+)', r' \1', input)


def pathToAddress(path, common):
    rem = path.replace(common, '')
    if rem.startswith('\\'):
        rem = rem[1:]
    return '::'.join(os.path.normpath(rem).split(os.path.sep))
