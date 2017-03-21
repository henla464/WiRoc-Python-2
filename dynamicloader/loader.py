import os, importlib, inspect
import logging

class Loader(object):

    @staticmethod
    def ImportModule(moduleAbsoluteName):
        logging.info("Loader::ImportModule() " + moduleAbsoluteName)
        try:
            return importlib.import_module(moduleAbsoluteName)
        except Exception as myex:
            logging.error("Loader::ImportModule() Import exception")
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
                    logging.debug("Loader::GetFirstClassFromModule() Class name: "  + name)
                    return moduleObject
                else:
                    logging.debug("Loader::GetFirstClassFromModule() Class name: " + name + " doesn't end in " + suffix)
            else:
                logging.debug("Loader::GetFirstClassFromModule() Class name: " + name + " isn't a class")