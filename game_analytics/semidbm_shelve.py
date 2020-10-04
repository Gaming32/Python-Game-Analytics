from shelve import Shelf
import semidbm


class SemidbmShelf(Shelf):
    """Shelf implementation using the "semidbm" dbm interface.

    This is initialized with the filename for the dbm database.
    See the module's __doc__ string for an overview of the interface.
    """

    def __init__(self, filename, flag='c', protocol=None, writeback=False):
        Shelf.__init__(self, semidbm.open(filename, flag), protocol, writeback)

    def compact(self):
        self.dict.compact()


open = SemidbmShelf
