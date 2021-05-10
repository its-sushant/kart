import json
import logging

from sqlalchemy.exc import OperationalError

from .db import annotations_session, KartAnnotation

L = logging.getLogger(__name__)


class DiffAnnotations:
    def __init__(self, repo):
        self.repo = repo

    def _object_id(self, base_rs, target_rs):
        # this is actually symmetric, so we can marginally increase hit rate by sorting first
        tree_ids = sorted(rs.tree.id for rs in (base_rs, target_rs))
        return f"{tree_ids[0]}...{tree_ids[1]}"

    def store(self, *, base_rs, target_rs, annotation_type, data):
        """
        Stores a diff annotation to the repo's sqlite database,
        and returns the annotation itself.

        base_rs: base RepoStructure object for this diff (revA in a 'revA...revB' diff)
        target_rs: target RepoStructure object for this diff (revB in a 'revA...revB' diff)
        """
        assert isinstance(data, dict)
        object_id = self._object_id(base_rs, target_rs)
        data = json.dumps(data)
        try:
            with annotations_session(self.repo) as session:
                L.debug(
                    "storing: %s for %s: %s",
                    annotation_type,
                    object_id,
                    data,
                )
                session.add(
                    KartAnnotation(
                        object_id=object_id,
                        annotation_type=annotation_type,
                        data=data,
                    )
                )
        except OperationalError as e:
            # ignore errors from readonly databases.
            if "readonly database" in str(e):
                L.info("Can't store annotation; annotations.db is read-only")
            else:
                raise
        return data

    def get(self, *, base_rs, target_rs, annotation_type):
        """
        Returns a diff annotation from the sqlite database.
        Returns None if it isn't found.

        base_rs: base RepoStructure object for this diff (revA in a 'revA...revB' diff)
        target_rs: target RepoStructure object for this diff (revB in a 'revA...revB' diff)
        """
        with annotations_session(self.repo) as session:
            object_id = self._object_id(base_rs, target_rs)
            for annotation in session.query(KartAnnotation).filter(
                KartAnnotation.annotation_type == annotation_type,
                KartAnnotation.object_id == object_id,
            ):
                data = annotation.json
                L.debug(
                    "retrieved: %s for %s: %s",
                    annotation_type,
                    object_id,
                    data,
                )
                return data
            else:
                L.debug(
                    "missing: %s for %s",
                    annotation_type,
                    object_id,
                )
                return None
