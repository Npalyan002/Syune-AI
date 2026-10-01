from dataclasses import replace
import pytest
from syune.core import ActivationProfileId
from syune.cognition import ActivationProfileVersion,CognitiveBudget,GLOBAL_HARD_LIMITS,ProfileError,ProfileErrorCode,ProfileName,ProfileRegistry,effective_budget

def test_registry_builtins_default_explicit_duplicate_and_fingerprint():
    registry=ProfileRegistry();profiles=registry.list()
    assert {x.name for x in profiles}==set(ProfileName)
    general=registry.resolve();assert general.name is ProfileName.GENERAL
    assert registry.resolve(general.id) is general and general.fingerprint==ProfileRegistry().resolve().fingerprint
    with pytest.raises(ProfileError) as error:registry.resolve(ActivationProfileId.new())
    assert error.value.code is ProfileErrorCode.INVALID_PROFILE
    with pytest.raises(ProfileError):registry.register(general)

def test_inactive_incompatible_and_global_clipping():
    general=ProfileRegistry().resolve()
    inactive=replace(general,id=ActivationProfileId.new(),name=ProfileName.CREATIVE,status=type(general.status).INACTIVE)
    with pytest.raises(ProfileError) as error:ProfileRegistry((inactive,)).resolve(inactive.id)
    assert error.value.code is ProfileErrorCode.PROFILE_INACTIVE
    incompatible=replace(general,id=ActivationProfileId.new(),name=ProfileName.SYSTEMS,core_version="999")
    with pytest.raises(ProfileError) as error:ProfileRegistry((incompatible,)).resolve(incompatible.id)
    assert error.value.code is ProfileErrorCode.PROFILE_INCOMPATIBLE
    huge=CognitiveBudget(9,999,999,999,999,9,999,999,9999)
    profile=replace(general,budget=huge);effective,clipped=effective_budget(huge,profile)
    assert effective==GLOBAL_HARD_LIMITS and "max_recall_candidates" in clipped

def test_versions_are_typed():
    with pytest.raises(ValueError):ActivationProfileVersion(0)
