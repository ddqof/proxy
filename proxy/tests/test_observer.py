import pytest

from proxy._observer import Observer
from proxy._limited_resource import LimitedResource


@pytest.fixture()
def def_obs():
    return Observer(
        [LimitedResource("localhost", 100)],
        ["black_list_host"]
    )


def test_link_in_black_list_equals_request_link(def_obs):
    res = def_obs.is_link_in_black_list("black_list_host")
    assert res is True


def test_multiple_links_in_black_list():
    obs = Observer([], ["youtube.com", "vk.com", "google.com"])
    res = obs.is_link_in_black_list("vk.com")
    assert res is True


def test_link_is_not_in_black_list(def_obs):
    res = def_obs.is_link_in_black_list("google.com")
    assert res is False


def test_update_from_initial_state(def_obs):
    res = def_obs.update_state("localhost", 80)
    assert res == "80 WAS SPENT FOR localhost"


def test_same_state_few_times(def_obs):
    def_obs.update_state("localhost", 40)
    res = def_obs.update_state("localhost", 50)
    assert res == "90 WAS SPENT FOR localhost"


def test_update_state_not_restricted_resource(def_obs):
    res = def_obs.update_state("some_other_page", 220)
    assert res is None


def test_is_data_lim_not_reached_without_requests(def_obs):
    res = def_obs.is_data_lim_reached("localhost")
    assert res is False


def test_is_data_lim_not_reached_with_requests(def_obs):
    def_obs.update_state("localhost", 80)
    res = def_obs.is_data_lim_reached("localhost")
    assert res is False


def test_is_data_lim_truly_reached(def_obs):
    def_obs.update_state("localhost", 200)
    res = def_obs.is_data_lim_reached("localhost")
    assert res is True

# TODO: проверить паттерны
