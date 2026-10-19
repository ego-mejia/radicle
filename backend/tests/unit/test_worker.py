from radicle import cli
from radicle.services import queue
from radicle.worker import app as worker_app


def test_conninfo() -> None:
    url = "postgresql+asyncpg://u:p@db:5432/radicle"
    assert worker_app.conninfo(url) == "postgresql://u:p@db:5432/radicle"
    assert worker_app.conninfo("postgresql://x/y") == "postgresql://x/y"


def test_build_app_registers_every_handler() -> None:
    app = worker_app.build_app()
    assert set(queue.HANDLERS) <= set(app.tasks)


def test_cli_requires_a_command(capsys) -> None:  # type: ignore[no-untyped-def]
    try:
        cli.main([])
    except SystemExit as exc:
        assert exc.code == 2
    assert "worker" in capsys.readouterr().err
