import faroes.fastparticleslowing
from scipy.constants import pi
from faroes.units import add_local_units
import numpy as np

import openmdao.api as om
from openmdao.utils.assert_utils import assert_check_partials
from openmdao.utils.assert_utils import assert_near_equal

import unittest


class TestCriticalSlowingEnergyRatio(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()
        prob.model = faroes.fastparticleslowing.CriticalSlowingEnergyRatio()
        prob.setup(force_alloc_complex=True)
        self.prob = prob

    def test_partials(self):
        prob = self.prob
        prob.run_driver()
        check = prob.check_partials(out_stream=None, method='cs')
        assert_check_partials(check)


class TestFastParticleHeatingFractions(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()

        prob.model = faroes.fastparticleslowing.FastParticleHeatingFractions()

        prob.setup(force_alloc_complex=True)

        prob.set_val('W/Wc', 1.0)
        self.prob = prob

    def test_partials(self):
        prob = self.prob
        prob.run_driver()
        check = prob.check_partials(out_stream=None, method='cs')
        assert_check_partials(check)

    def test_value(self):
        prob = self.prob
        prob.run_driver()
        expected = (2 / 9) * (3**(1 / 2) * np.pi - 3 * np.log(2))
        assert_near_equal(prob["f_i"], expected, tolerance=1e-5)


class TestSlowingTimeOnElectrons(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()
        prob.model = faroes.fastparticleslowing.SlowingTimeOnElectrons()
        prob.setup(force_alloc_complex=True)

        prob.set_val("At", 2, units='u')
        prob.set_val("Zt", 1)
        prob.set_val("ne", 1.06e20, units='m**-3')
        prob.set_val("Te", 9.20, units='keV')
        prob.set_val("logΛe", 17.37)

        self.prob = prob

    def test_partials(self):
        prob = self.prob
        check = prob.check_partials(out_stream=None, method='cs')
        assert_check_partials(check)

    def test_value(self):
        prob = self.prob
        prob.run_driver()
        expected = 0.599  # seconds
        assert_near_equal(prob["ts"], expected, tolerance=1e-2)


class TestSlowingThermalizationTime(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()

        prob.model = faroes.fastparticleslowing.SlowingThermalizationTime()

        prob.setup(force_alloc_complex=True)

        prob.set_val('W/Wc', 1.0)
        prob.set_val('ts', 1.0)
        self.prob = prob

    def test_partials(self):
        prob = self.prob
        check = prob.check_partials(out_stream=None, method='cs')
        assert_check_partials(check)

    def test_value(self):
        prob = self.prob
        prob.run_driver()
        assert_near_equal(prob["τth"], 0.231049, tolerance=1e-5)


class TestAverageEnergyWhileSlowing(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()
        prob.model = faroes.fastparticleslowing.AverageEnergyWhileSlowing()
        prob.setup(force_alloc_complex=True)

        prob.set_val('W/Wc', 1.0)
        prob.set_val('Wc', 2.0, units='keV')
        self.prob = prob

    def test_partials(self):
        prob = self.prob
        check = prob.check_partials(out_stream=None, method='cs')
        assert_check_partials(check)

    def test_value(self):
        prob = self.prob
        prob.run_driver()
        expected = (9 - 2 * 3**(1 / 2) * pi + np.log(64)) / np.log(8)
        assert_near_equal(prob["Wbar"], expected, tolerance=1e-5)


class TestFastParticleSlowing(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()
        add_local_units()

        prob.model.add_subsystem('ivc',
                                 om.IndepVarComp('ni',
                                                 val=np.ones(2),
                                                 units='n20'),
                                 promotes_outputs=["*"])
        prob.model.add_subsystem(
            'fps',
            faroes.fastparticleslowing.FastParticleSlowing(),
            promotes_inputs=["*"])

        prob.setup()
        prob.set_val("ni", np.array([0.5e20, 0.5e20]), units='m**-3')
        prob.set_val("Ai", [2, 3], units='u')
        prob.set_val("Zi", [1, 1])

        prob.set_val("At", 2, units='u')
        prob.set_val("Zt", 1)
        prob.set_val("ne", 1.06e20, units='m**-3')
        prob.set_val("Te", 9.20, units='keV')
        prob.set_val("logΛe", 17.37)
        prob.set_val('Wt', 500, units='keV')
        self.prob = prob

    def test_slowing_time_value(self):
        prob = self.prob
        expectedτth = 0.272  # seconds
        prob.run_driver()
        assert_near_equal(prob["fps.τth"], expectedτth, tolerance=1e-3)

    def test_average_energy_while_slowing(self):
        prob = self.prob
        # Menard gets 243 keV, so his calculation is close!
        expectedWbar = 248.4  # keV
        prob.run_driver()
        assert_near_equal(prob["fps.Wbar"], expectedWbar, tolerance=1e-3)


class TestCriticalSlowingEnergy(unittest.TestCase):
    def setUp(self):
        prob = om.Problem()
        add_local_units()

        prob.model.add_subsystem('ivc',
                                 om.IndepVarComp('ni',
                                                 val=np.ones(2),
                                                 units='n20'),
                                 promotes_outputs=["*"])
        prob.model.add_subsystem(
            'cse',
            faroes.fastparticleslowing.CriticalSlowingEnergy(),
            promotes_inputs=["*"])

        prob.setup(force_alloc_complex=True)

        prob.set_val("At", 2, units='u')
        prob.set_val("ne", 1.0e20, units='m**-3')
        prob.set_val("Te", 1.0, units='keV')
        prob.set_val("ni", np.array([0.5e20, 0.5e20]), units='m**-3')
        prob.set_val("Ai", [2, 3], units='u')
        prob.set_val("Zi", [1, 1])
        self.prob = prob

    def test_partials(self):
        prob = self.prob
        check = prob.check_partials(out_stream=None, method='cs')
        assert_check_partials(check)

    def test_value(self):
        prob = self.prob
        prob.set_val("At", 2, units='u')
        prob.set_val("ne", 1.06e20, units='m**-3')
        prob.set_val("Te", 9.20, units='keV')
        prob.set_val("ni", np.array([0.53e20, 0.53e20]), units='m**-3')
        prob.set_val("Ai", [2, 3], units='u')
        prob.set_val("Zi", [1, 1])
        prob.run_driver()
        assert_near_equal(prob["cse.W_crit"], 256.4, tolerance=1e-3)


if __name__ == '__main__':
    unittest.main()
