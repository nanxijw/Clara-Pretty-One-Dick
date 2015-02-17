#Embedded file name: walk\__init__.py
"""
This is adapted from os.walk, to work with respaths.
"""
import blue

def walk(top, topdown = True, onerror = None):
    """Directory tree generator.
    
    For each directory in the directory tree rooted at top (including top
    itself, but excluding '.' and '..'), yields a 3-tuple
    
        dirpath, dirnames, filenames
    
    dirpath is a string, the path to the directory.  dirnames is a list of
    the names of the subdirectories in dirpath (excluding '.' and '..').
    filenames is a list of the names of the non-directory files in dirpath.
    Note that the names in the lists are just names, with no path components.
    To get a full path (which begins with top) to a file or directory in
    dirpath, do os.path.join(dirpath, name).
    
    If optional arg 'topdown' is true or not specified, the triple for a
    directory is generated before the triples for any of its subdirectories
    (directories are generated top down).  If topdown is false, the triple
    for a directory is generated after the triples for all of its
    subdirectories (directories are generated bottom up).
    
    When topdown is true, the caller can modify the dirnames list in-place
    (e.g., via del or slice assignment), and walk will only recurse into the
    subdirectories whose names remain in dirnames; this can be used to prune
    the search, or to impose a specific order of visiting.  Modifying
    dirnames when topdown is false is ineffective, since the directories in
    dirnames have already been generated by the time dirnames itself is
    generated.
    
    By default errors from the blue.os.listdir() call are ignored.  If
    optional arg 'onerror' is specified, it should be a function; it
    will be called with one argument, an os.error instance.  It can
    report the error to continue with the walk, or raise the exception
    to abort the walk.  Note that the filename is available as the
    filename attribute of the exception object.
    
    """
    if top.endswith('/'):
        top = top[:-1]
    try:
        names = blue.paths.listdir(top)
    except blue.error as err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    for name in names:
        if blue.paths.isdir(u'/'.join((top, name))):
            dirs.append(name)
        else:
            nondirs.append(name)

    if topdown:
        yield (top, dirs, nondirs)
    for name in dirs:
        new_path = u'/'.join((top, name))
        for x in walk(new_path, topdown, onerror):
            yield x

    if not topdown:
        yield (top, dirs, nondirs)
