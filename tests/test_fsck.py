import pytest


H = pytest.helpers.helpers()


def test_fsck(data_working_copy, geopackage, cli_runner):
    with data_working_copy("points") as (repo, wc):
        db = geopackage(wc)

        r = cli_runner.invoke(["fsck"])
        assert r.exit_code == 0, r

        # introduce a feature mismatch
        assert H.row_count(db, H.POINTS_LAYER) == H.POINTS_ROWCOUNT
        assert H.row_count(db, '.sno-track') == 0

        with db:
            db.execute(f"UPDATE {H.POINTS_LAYER} SET name='fred' WHERE fid=1;")
            db.execute("""DELETE FROM ".sno-track" WHERE pk='1';""")

        r = cli_runner.invoke(["fsck"])
        assert r.exit_code == 1, r

        r = cli_runner.invoke(["fsck", "--reset-dataset=nz_pa_points_topo_150k"])
        assert r.exit_code == 0, r

        assert H.row_count(db, H.POINTS_LAYER) == H.POINTS_ROWCOUNT
        assert H.row_count(db, '.sno-track') == 0

        r = cli_runner.invoke(["fsck"])
        assert r.exit_code == 0, r
