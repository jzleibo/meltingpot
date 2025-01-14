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
"""Tests for substrate."""

from absl.testing import absltest
from absl.testing import parameterized

from meltingpot.python import substrate
from meltingpot.python.testing import substrates as test_utils


@parameterized.named_parameters(
    (name, name) for name in substrate.AVAILABLE_SUBSTRATES)
class SubstrateTestCase(test_utils.SubstrateTestCase):

  def test_matches_spec(self, name):
    config = substrate.get_config(name)
    env = self.enter_context(substrate.build(config))
    with self.subTest('discount'):
      self.assert_discount_matches_spec(env)
    with self.subTest('reward'):
      self.assert_reward_matches_spec(env)
    with self.subTest('observation'):
      self.assert_observation_matches_spec(env)

  def test_spec_in_config_matches_environment(self, name):
    config = substrate.get_config(name)
    action_spec = [config.action_spec] * config.num_players
    reward_spec = [config.timestep_spec.reward] * config.num_players
    observation_spec = [
        dict(config.timestep_spec.observation)] * config.num_players
    with substrate.build(config) as env:
      with self.subTest('discount_spec'):
        self.assertSequenceEqual(env.action_spec(), action_spec)
      with self.subTest('reward_spec'):
        self.assertSequenceEqual(env.reward_spec(), reward_spec)
      with self.subTest('discount_spec'):
        self.assertEqual(env.discount_spec(), config.timestep_spec.discount)
      with self.subTest('observation_spec'):
        self.assertSequenceEqual(env.observation_spec(), observation_spec)

if __name__ == '__main__':
  absltest.main()
