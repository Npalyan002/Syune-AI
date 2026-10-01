import json
import pytest
from syune.cli.app import INVALID_INPUT,NOT_INITIALIZED,SUCCESS,_parser,run


def test_cli_init_health_status_config_upgrade_and_exit_codes(tmp_path,capsys):
    root=(tmp_path/'state').resolve();args=['--state-root',str(root),'--json']
    assert run(['health',*args])==NOT_INITIALIZED;capsys.readouterr()
    assert run(['init',*args])==SUCCESS;first=json.loads(capsys.readouterr().out)
    assert run(['init',*args])==SUCCESS;second=json.loads(capsys.readouterr().out)
    assert first['instance_id']==second['instance_id'] and second['created'] is False
    assert run(['health',*args])==SUCCESS
    assert json.loads(capsys.readouterr().out)['overall']=='HEALTHY'
    assert run(['status',*args])==SUCCESS
    assert json.loads(capsys.readouterr().out)['telemetry']=='OFF'
    assert run(['config','show',*args])==SUCCESS
    assert json.loads(capsys.readouterr().out)['state']['root']==str(root)
    assert run(['config','validate',*args])==SUCCESS
    assert json.loads(capsys.readouterr().out)['valid'] is True
    assert run(['upgrade','check',*args])==SUCCESS
    assert json.loads(capsys.readouterr().out)['migration_required'] is False
    bad=(tmp_path/'bad.toml').resolve();bad.write_text('[retrieval]\nmax_results=-1')
    assert run(['config','validate','--config',str(bad)])==INVALID_INPUT


def test_version_subcommand(capsys):
    assert run(['version','--json'])==SUCCESS
    assert json.loads(capsys.readouterr().out)['version']=='1.0.0'


def test_invalid_command_uses_argparse_exit_code_two():
    with pytest.raises(SystemExit) as error:_parser().parse_args(['unknown'])
    assert error.value.code==2


def test_global_options_work_before_command(tmp_path,capsys):
    root=(tmp_path/'state').resolve()
    assert run(['--state-root',str(root),'--json','init'])==SUCCESS
    assert json.loads(capsys.readouterr().out)['state_root']==str(root)
