import os
import pytest
from syune.product.config import load_config


def test_precedence_defaults_file_environment_cli(tmp_path, monkeypatch):
    file_root=(tmp_path/'file').resolve();env_root=(tmp_path/'env').resolve();cli_root=(tmp_path/'cli').resolve()
    study=(tmp_path/'study').resolve();study.mkdir();config=(tmp_path/'config.toml').resolve()
    config.write_text(f'[state]\nroot="{file_root.as_posix()}"\n[study]\nroots=["{study.as_posix()}"]\n[retrieval]\nmax_results=12\n[logging]\nlevel="WARNING"\n')
    from_file=load_config(cli_config=config)
    assert from_file.state.root==file_root and from_file.retrieval.max_results==12
    monkeypatch.setenv('SYUNE_STATE_ROOT',str(env_root));monkeypatch.setenv('SYUNE_LOG_LEVEL','ERROR')
    from_env=load_config(cli_config=config)
    assert from_env.state.root==env_root and from_env.logging.level=='ERROR'
    from_cli=load_config(cli_config=config,cli_state_root=cli_root,cli_log_level='DEBUG')
    assert from_cli.state.root==cli_root and from_cli.logging.level=='DEBUG'


@pytest.mark.parametrize('body',["unknown=1",'[retrieval]\nmax_results=101',
    '[logging]\nlevel="TRACE"','[study]\nroots=["relative"]','[mcp]\nshadow_read_only="yes"'])
def test_malformed_or_unsafe_config_fails_closed(tmp_path,body):
    config=(tmp_path/'config.toml').resolve();config.write_text(body)
    with pytest.raises(ValueError):load_config(cli_config=config)


def test_environment_safety_bounds_and_telemetry(tmp_path,monkeypatch):
    monkeypatch.setenv('SYUNE_MAX_RECALL_RESULTS','101')
    with pytest.raises(ValueError):load_config(cli_state_root=tmp_path.resolve())
    monkeypatch.delenv('SYUNE_MAX_RECALL_RESULTS');monkeypatch.setenv('SYUNE_TELEMETRY','1')
    assert load_config(cli_state_root=tmp_path.resolve()).telemetry is False
