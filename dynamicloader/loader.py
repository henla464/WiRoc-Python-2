import os, importlib, inspect
import logging

class Loader(object):
    WiRocLogger = logging.getLogger('WiRoc')

    @staticmethod
    def ImportModule(moduleAbsoluteName):
        try:
            return importlib.import_module(moduleAbsoluteName)
        except Exception as myex:
            Loader.WiRocLogger.error("Loader::ImportModule() Import exception: %s" %moduleAbsoluteName)
            Loader.WiRocLogger.error(myex)
            pass

        return None

    @staticmethod
    def IsPythonFile(uri, fileName):
        isFile = os.path.isfile(os.path.join(uri, fileName))
        nameWithoutExt, ext = os.path.splitext(fileName)
        return isFile and ext == ".py" and nameWithoutExt != "__init__"

    @staticmethod
    def GetModuleName(uri, fileName):
        nameWithoutExt, ext = os.path.splitext(fileName)
        return uri + "." + nameWithoutExt

    @staticmethod
    def ImportDirectory(directory, absl=False):
        if not absl:
            uri = os.path.normpath(os.path.join(os.path.dirname(__file__), "../" + directory))

        moduleAbsoluteNames = [Loader.GetModuleName(directory, f) for f in os.listdir(uri) if Loader.IsPythonFile(uri,f)]

        mods = []
        for moduleAbsoluteName in moduleAbsoluteNames:
            mods.append(Loader.ImportModule(moduleAbsoluteName))

        return mods

    @staticmethod
    def GetFirstClassFromModule(module, suffix):
        for name, moduleObject in inspect.getmembers(module):
            if inspect.isclass(moduleObject):
                if name.endswith(suffix):
                    #Loader.WiRocLogger.debug("Loader::GetFirstClassFromModule() Class name: "  + name)
                    return moduleObject
            else:
                Loader.WiRocLogger.debug("Loader::GetFirstClassFromModule() Class name: " + name + " isn't a class")
        Loader.WiRocLogger.debug("Loader::GetFirstClassFromModule() No class member found")
        return None