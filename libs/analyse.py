#-*- coding:utf-8 -*-


'''
Bugtrack, a sublime plugin for finding security bugs.
-----------------------------------------------------------------------
Copyright (c) 2016 alpha1e0
'''


import os
import sys
import time


from libs.commons import FileError
from libs.commons import YamlConf
from libs.commons import getPluginPath
from libs import engines



class AnalyseResult(object):
    def __init__(self):
        self._data = {}
        self._patternList = []
        self._filenameList = []


    def _addPattern(self, pattern):
        '''
        Add a pattern string to the patternList and return the index, \
            if the pattern dose exsits just return the index
        '''
        for i in range(len(self._patternList)):
            if self._patternList[i] == pattern:
                patternIndex = i
                break
        else:
            self._patternList.append(pattern)
            patternIndex = len(self._patternList)-1

        return patternIndex


    def _addFilename(self, filename):
        '''
        Add a file name string to the filenameList and return the index, \
            if the file name dose exsits just return the index
        '''
        for i in range(len(self._filenameList)):
            if self._filenameList[i] == filename:
                fileIndex = i
                break
        else:
            self._filenameList.append(filename)
            fileIndex = len(self._filenameList)-1

        return fileIndex


    def add(self, ftype, pattern, filename, matchs):
        patternIndex = self._addPattern(pattern)
        fileIndex = self._addFilename(filename)

        if ftype not in self._data:
            self._data[ftype] = {}

        if patternIndex not in self._data[ftype]:
            self._data[ftype][patternIndex] = {}

        if fileIndex not in self._data[ftype][patternIndex]:
            self._data[ftype][patternIndex][fileIndex] = []

        self._data[ftype][patternIndex][fileIndex] = matchs


    @property
    def _banner(self):
        banner = "Code analyse result.\n"
        banner = banner + "{0} created.\n".format(\
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        banner = banner + "Powered by bugtrack.\n"

        return banner


    def toString(self):
        def formatMatchEntry(matchEntry):
            return "   " + str(matchEntry[0]) + ": " + matchEntry[1].rstrip("\n")

        result = ""
        result = result + self._banner + "\n"

        for ftype, typeResult in self._data.items():
            blockStr = ""
            for patternIndex, patternResult in typeResult.items():
                for fileIndex, fileResult in patternResult.items():
                    if fileResult:
                        blockStr = "\n".join(["{{{0}}}[{1}]".format(ftype, \
                            self._patternList[patternIndex]),\
                            "{0}:".format(self._filenameList[fileIndex])])

                        matchStr = ""
                        for match in fileResult:
                            #print match
                            matchStr = matchStr + "\n" + formatMatchEntry(match)

                        blockStr = blockStr + matchStr + "\n"

                        result = result + "\n" + blockStr

        return result



class FileSet(object):
    def __init__(self, directory):
        if not os.path.exists(directory):
            raise FileError("FileSet cannot find directory '{0}'".format(directory))

        self.directory = directory

        self._fileMapping = self._loadFileMappingCfg()

        self._fileSet = self._initFileSet()


    def _loadFileMappingCfg(self):
        cfgFile = os.path.join(getPluginPath(), "data", "filemap")

        return YamlConf(cfgFile)


    def _getFileType(self, fileName):
        '''
        use fileName to generate file entry
        '''
        extPos = fileName.rfind(".")
        if extPos == -1:
            return "raw"
        else:
            ext = fileName[extPos:]
            if ext in self._fileMapping:
                return self._fileMapping[ext]
            else:
                return "raw"


    def _initFileSet(self):
        # fileSet {filetype, files}
        fileSet = {}

        for path, dirlist, filelist in os.walk(self.directory):
            for file in filelist:
                fileName = os.path.join(path,file)
                fileType = self._getFileType(fileName)
                if fileType not in fileSet:
                    fileSet[fileType] = []

                fileSet[fileType].append(fileName)

        return fileSet


    def _loadEngine(self, fileType):
        for member in dir(engines):
            if member.lower().startswith(fileType):
                engineClass = getattr(engines, member)
        else:
            engineClass = engines.Engine

        return engineClass


    def _loadSigs(self, ftype):
        sigFileDir = os.path.join(os.path.dirname(os.path.dirname(__file__)),\
             "data", "sigs")

        sigFiles = os.listdir(sigFileDir)

        for fname in sigFiles:
            if fname.startswith(ftype) and fname.endswith(".sig"):
                sigFile = os.path.join(sigFileDir, fname)
                break
        else:
            raise FileError("can not find signature file {0}".format(ftype))

        sigs = YamlConf(sigFile)

        return sigs if sigs else []


    def doAnalyse(self):
        '''
        @returns:
            {type : {pattern: {filename:[matchs]}}
        '''
        analyseResult = AnalyseResult()

        for ftype, files in self._fileSet.items():
            sigs = self._loadSigs(ftype)
            engineClass = self._loadEngine(ftype)
            for sig in sigs:
                for file in files:
                    engine = engineClass()
                    result = engine.analyse(file, sig)
                    analyseResult.add(ftype, sig, file, result)

        return analyseResult
