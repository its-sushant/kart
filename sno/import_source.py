import click
import functools

from .meta_items import META_ITEM_NAMES
from .schema import Schema


class ImportSource:
    """
    A dataset-like interface that can be imported as a dataset.
    A read-only interface.
    """

    @classmethod
    def check_valid(cls, import_sources, param_hint=None):
        """Given an iterable of ImportSources, checks that all are fully specified and none of their dest_paths collide."""
        dest_paths = {}
        for s1 in import_sources:
            s1.check_fully_specified()
            dest_path = s1.dest_path.strip("/")
            if dest_path not in dest_paths:
                dest_paths[dest_path] = s1
            else:
                s2 = dest_paths[dest_path]
                raise click.BadParameter(
                    f"Can't import both {s1} and {s2} as {dest_path}",
                    param_hint=param_hint,
                )

    def check_fully_specified(self):
        """
        Some ImportSources can be constructed only partially specified, but they will not work as an import source
        until they are fully specified. This checks that self is fully specified and raises an error if it is not.
        """
        pass

    @property
    def dest_path(self):
        """
        The destination path where this dataset should be imported.
        ImportSource.dest_path can be set, otherwise defaults to ImportSource.default_dest_path()
        """
        if hasattr(self, "_dest_path"):
            return self._dest_path
        return self.default_dest_path()

    def default_dest_path(self):
        """
        The default destination path where this dataset should be imported.
        This should be generated based on the source path / source table name of the ImportSource.
        """
        raise NotImplementedError()

    @dest_path.setter
    def dest_path(self, dest_path):
        self._dest_path = dest_path

    def get_meta_item(self, name):
        """Find or generate a V2 meta item."""
        # If self.get_gpkg_meta_item works already, this method can be implemented as follows:
        # >>> return gpkg_adapter.generate_v2_meta_item(self, name)
        raise NotImplementedError()

    def get_gpkg_meta_item(self, name):
        """Find or generate a gpkg / V1 meta item."""
        # If self.get_meta_item works already, this method can be implemented as follows:
        # >>> return gpkg_adapter.generate_gpkg_meta_item(self, name)

        raise NotImplementedError()

    def iter_meta_items(self):
        """Iterates over all the meta items that need to be imported."""
        for name in META_ITEM_NAMES:
            meta_item = self.get_meta_item(name)
            if meta_item is not None:
                yield name, meta_item

        for identifier, definition in self.iter_crs_definitions():
            yield f"crs/{identifier}.wkt", definition

    def iter_crs_definitions(self):
        """
        Yields a (identifier, definition) tuple for every CRS definition.
        The identifier should be a string that uniquely identifies the CRS eg "EPSG:4326"
        The definition should be a string containing a WKT definition eg 'GEOGCS["WGS 84"...'
        """
        raise NotImplementedError()

    def get_crs_definition(self, identifier=None):
        """
        Returns the CRS definition with the given identifer,
        or the only CRS definition if no identifer is supplied.
        """
        # Subclasses may overrdie this to make it more efficient.
        all_crs_definitions = dict(self.iter_crs_definitions())
        if identifier is not None:
            return all_crs_definitions[identifier]
        num_defs = len(all_crs_definitions)
        if num_defs == 1:
            return next(iter(all_crs_definitions.values()))
        raise ValueError(
            f"get_crs_definition() only works when there is exactly 1 CRS definition, but there is {num_defs}"
        )

    @property
    @functools.lru_cache(maxsize=1)
    def schema(self):
        """Convenience method for loading the schema.json into a Schema object"""
        return Schema.from_column_dicts(self.get_meta_item("schema.json"))

    def features(self):
        """
        Yields a dict for every feature. Dicts contain key-value pairs for each feature property,
        and geometries use sno.geometry.Geometry objects, as in the following example:
        {
            "fid": 123,
            "geom": Geometry(b"..."),
            "name": "..."
            "last-modified": "..."
        }
        """
        raise NotImplementedError()

    @property
    def feature_count(self):
        """Returns the number of features in self.features"""
        # Subclasses should generally override this to make it more efficient:
        count = 0
        for f in self.features():
            count += 1
        return count

    def __enter__(self):
        """Some import sources have resources that need to be opened and closed."""
        pass

    def __exit__(self, *args):
        """Some import sources have resources that need to be opened and closed."""
        pass

    def __str__(self):
        return f"{self.__class__.__name__}"

    def import_source_desc(self):
        """Return a description of this ImportSource."""
        # Subclasses should override if str() does not return the right information.
        return f"Import from {self} to {self.dest_path}/"

    def aggregate_import_source_desc(self, import_sources):
        """
        Return a description of this collection of import_sources (which should contain self).
        For example:

        Import 3 datasets from example.gpkg:
        first_table
        second_dataset (from second_table)
        third_table
        """
        # Subclasses should override this if a more useful aggregate description can be generated.
        return "\n".join(s.import_source_desc() for s in import_sources)
