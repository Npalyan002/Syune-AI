import json
import pytest
from syune.product.config import load_config
from syune.product.runtime import SyuneRuntime
from syune.product.state import DATABASES,initialize_state,load_metadata,metadata_path,upgrade_check


def config(root):return load_config(cli_state_root=root.resolve())


def test_init_is_idempotent_isolated_and_runtime_closes(tmp_path):
    a=config(tmp_path/'a');b=config(tmp_path/'b')
    first,created=initialize_state(a);second,again=initialize_state(a);other,_=initialize_state(b)
    assert created and not again and first.instance_id==second.instance_id!=other.instance_id
    with SyuneRuntime.open(a) as runtime:
        assert runtime.health()['overall']=='HEALTHY' and runtime.memory.iter_entities()==()
    assert runtime.closed
    runtime=SyuneRuntime.open(b)
    try:assert runtime.memory.iter_entities()==()
    finally:runtime.close()


def test_partial_init_recovers_but_initialized_missing_db_blocks(tmp_path):
    cfg=config(tmp_path/'state');cfg.state.root.mkdir();(cfg.state.root/'memory').mkdir()
    initialize_state(cfg)
    (cfg.state.root/DATABASES['execution']).unlink()
    with pytest.raises(ValueError,match='missing component'):initialize_state(cfg)
    with pytest.raises(ValueError,match='missing component'):SyuneRuntime.open(cfg)


def test_uninitialized_future_corrupt_and_unknown_state_are_explicit(tmp_path):
    root=(tmp_path/'state').resolve();cfg=config(root)
    with pytest.raises(FileNotFoundError):load_metadata(root)
    root.mkdir();(root/'unknown.bin').write_bytes(b'x')
    with pytest.raises(ValueError,match='unknown entries'):initialize_state(cfg)
    (root/'unknown.bin').unlink();initialize_state(cfg)
    path=metadata_path(root);value=json.loads(path.read_text());value['state_schema_version']=999;path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='unsupported product'):upgrade_check(root)
    path.write_text('{')
    with pytest.raises(ValueError,match='corrupt'):load_metadata(root)


def test_state_relocation_is_independent_of_working_directory(tmp_path,monkeypatch):
    cfg=config(tmp_path/'state');metadata,_=initialize_state(cfg)
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir();monkeypatch.chdir(elsewhere)
    with SyuneRuntime.open(cfg) as runtime: assert runtime.metadata.instance_id==metadata.instance_id


def test_read_only_metadata_failure_is_explicit_and_opened_stores_close(tmp_path,monkeypatch):
    cfg=config(tmp_path/'state');initialize_state(cfg)
    import syune.product.runtime as module
    def denied(*_):raise PermissionError('read-only state')
    monkeypatch.setattr(module,'record_successful_open',denied)
    with pytest.raises(PermissionError,match='read-only'):SyuneRuntime.open(cfg)
