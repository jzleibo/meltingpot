# Copyright 2020 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Scenario factory."""

import collections
from collections.abc import Mapping, Set

import immutabledict
from ml_collections import config_dict

from meltingpot.python import bot as bot_factory
from meltingpot.python import substrate as substrate_factory
from meltingpot.python.configs import scenarios as scenario_configs
from meltingpot.python.utils.scenarios import scenario as scenario_lib
from meltingpot.python.utils.scenarios import substrate_transforms

SCENARIOS = frozenset(scenario_configs.SCENARIO_CONFIGS)
AVAILABLE_SCENARIOS = SCENARIOS


def _scenarios_by_substrate() -> Mapping[str, Set[str]]:
  """Returns a mapping from substrates to their scenarios."""
  scenarios_by_substrate = collections.defaultdict(list)
  for scenario_name, config in scenario_configs.SCENARIO_CONFIGS.items():
    scenarios_by_substrate[config.substrate].append(scenario_name)
  return immutabledict.immutabledict({
      substrate: frozenset(scenarios)
      for substrate, scenarios in scenarios_by_substrate.items()
  })


SCENARIOS_BY_SUBSTRATE = _scenarios_by_substrate()

PERMITTED_OBSERVATIONS = frozenset({
    # The primary visual input.
    'RGB',
    # Extra observations used in some substrates.
    'INVENTORY',
    'READY_TO_SHOOT',
})


def get_config(scenario_name: str) -> config_dict.ConfigDict:
  """Returns a config for the specified scenario.

  Args:
    scenario_name: Name of the scenario. Must be in AVAILABLE_SCENARIOS.
  """
  if scenario_name not in AVAILABLE_SCENARIOS:
    raise ValueError(f'Unknown scenario {scenario_name!r}')
  scenario = scenario_configs.SCENARIO_CONFIGS[scenario_name]
  substrate = substrate_factory.get_config(scenario.substrate)
  bots = {
      name: bot_factory.get_config(name)
      for name in set().union(*scenario.bots_by_role.values())
  }
  focal_player_roles = tuple(
      role for n, role in enumerate(scenario.roles) if scenario.is_focal[n]
  )
  focal_timestep_spec = substrate.timestep_spec._replace(
      observation=immutabledict.immutabledict({
          key: spec for key, spec in substrate.timestep_spec.observation.items()
          if key in PERMITTED_OBSERVATIONS
      }),
  )
  config = config_dict.create(
      substrate=substrate,
      roles=scenario.roles,
      is_focal=scenario.is_focal,
      num_players=sum(scenario.is_focal),
      bots=bots,
      bots_by_role=scenario.bots_by_role,
      substrate_transform=None,
      permitted_observations=set(PERMITTED_OBSERVATIONS),
      focal_player_roles=focal_player_roles,
      timestep_spec=focal_timestep_spec,
      action_spec=substrate.action_spec,
  )
  return config.lock()


def build(config: config_dict.ConfigDict) -> scenario_lib.Scenario:
  """Builds a scenario for the given config.

  Args:
    config: config resulting from `get_config`.

  Returns:
    The test scenario.
  """
  # TODO(b/227143834): pass roles to substrate when building.
  substrate = substrate_factory.build(config.substrate)
  if config.substrate_transform:
    substrate = config.substrate_transform(substrate)
  permitted_observations = set(substrate.observation_spec()[0])
  if not config.substrate_transform:
    permitted_observations &= config.permitted_observations
  # Add observations needed by some bots. These are removed for focal players.
  # TODO(b/258239516): remove this wrapper in a future release.
  substrate = substrate_transforms.with_tf1_bot_required_observations(substrate)
  bots = {
      bot_name: bot_factory.build(bot_config)
      for bot_name, bot_config in config.bots.items()
  }
  return scenario_lib.build_scenario(
      substrate=substrate,
      bots=bots,
      bots_by_role=config.bots_by_role,
      roles=config.roles,
      is_focal=config.is_focal,
      permitted_observations=permitted_observations)
