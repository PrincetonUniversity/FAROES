# This is an example of how to join components together

import openmdao.api as om
from faroes.simple_tf_magnet import MagnetRadialBuild
from faroes.elliptical_plasma import MenardPlasmaGeometry
from faroes.radialbuild import MenardSTRadialBuild
from faroes.configurator import UserConfigurator


class Machine(om.Group):
    def initialize(self):
        self.options.declare('config')

    def setup(self):
        config = self.options['config']

        self.add_subsystem("plasma",
                           MenardPlasmaGeometry(config=config),
                           promotes_inputs=["R0", "A"])

        self.add_subsystem("radial_build",
                           MenardSTRadialBuild(config=config),
                           promotes_inputs=['CS R_max', "A"])

        self.add_subsystem("magnets",
                           MagnetRadialBuild(config=config),
                           promotes_inputs=["R0"])
        self.connect('plasma.R_max', ['radial_build.plasma R_max'])
        self.connect('plasma.R_min', ['radial_build.plasma R_min'])

        self.connect('radial_build.Ob TF R_min', ['magnets.r_iu'])
        self.connect('radial_build.Ib TF R_min', ['magnets.r_is'])
        self.connect('radial_build.Ib TF R_max', ['magnets.r_ot'])

        self.connect('magnets.Ob TF R_out', ['radial_build.Ob TF R_out'])


if __name__ == "__main__":
    prob = om.Problem()

    uc = UserConfigurator()
    prob.model = Machine(config=uc)

    model = prob.model

    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options['optimizer'] = 'SLSQP'
    prob.driver.options['disp'] = True

    prob.model.add_design_var('A', lower=1.6, upper=2.0, ref=2.0)
    prob.model.add_design_var('CS R_max',
                              lower=0.02,
                              upper=0.2,
                              ref=0.3,
                              units='m')
    prob.model.add_design_var('magnets.f_im', lower=0.05, upper=1.0, ref=0.3)
    prob.model.add_design_var('magnets.j_HTS', lower=10, upper=300, ref=100)

    prob.model.add_objective('magnets.B0', scaler=-1)

    # set constraints
    prob.model.add_constraint('magnets.constraint_max_stress', lower=0)
    prob.model.add_constraint('magnets.constraint_B_on_coil', lower=0)
    prob.model.add_constraint('magnets.constraint_wp_current_density', lower=0)
    prob.model.add_constraint('magnets.A_s', lower=0)
    prob.model.add_constraint('magnets.A_m', lower=0)
    prob.model.add_constraint('magnets.A_t', lower=0)

    prob.setup()
    # prob.check_config(checks=['unconnected_inputs'])

    prob.set_val("magnets.f_im", 0.5)
    prob.set_val("CS R_max", 0.30)
    prob.set_val('R0', 3, units='m')
    prob.set_val('plasma.A', 1.7)
    prob.set_val('magnets.n_coil', 18)
    prob.set_val('magnets.windingpack.j_eff_max', 160)
    prob.set_val('magnets.windingpack.f_HTS', 0.76)
    prob.set_val("magnets.magnetstructure_props.Young's modulus", 220)

    prob.run_driver()

    all_inputs = prob.model.list_inputs(values=True)
    all_outputs = prob.model.list_outputs(values=True)
