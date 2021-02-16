# This is an example of how to join components together

import openmdao.api as om
from faroes.simple_tf_magnet import MagnetRadialBuild
from faroes.sauter_plasma import SauterPlasmaGeometry
from faroes.threearcdeecoil import ThreeArcDeeTFSet
from faroes.configurator import UserConfigurator
from faroes.util import SquaredLengthSubtraction

import numpy as np
from scipy.constants import pi

import matplotlib.pyplot as plt


class Machine(om.Group):
    def initialize(self):
        self.options.declare("config")

    def setup(self):
        config = self.options["config"]

        self.add_subsystem("plasma",
                           SauterPlasmaGeometry(config=config),
                           promotes_inputs=["R0", ("θ", "θ_for_d2"), "offset"],
                           promotes_outputs=["R_max", "R_min"])
        self.add_subsystem("coils",
                           ThreeArcDeeTFSet(),
                           promotes_inputs=["R0"],
                           promotes_outputs=["V_enc"])
        self.connect("plasma.blanket envelope θ", "coils.θ")
        self.add_subsystem("margin", SquaredLengthSubtraction())
        self.connect("coils.d_sq", "margin.b")
        self.connect("plasma.blanket envelope d_sq", "margin.a")

        self.add_subsystem(
            'ks', om.KSComp(width=40, units="m**2", ref=10,
                            rho=10, upper=0, add_constraint=True))
        self.connect("margin.c", "ks.g")


if __name__ == "__main__":
    prob = om.Problem()

    θ = np.linspace(0, 2 * pi, 40, endpoint=False)
    prob.model.add_subsystem("ivc",
                             om.IndepVarComp("θ_for_d2", val=θ),
                             promotes_outputs=["*"])

    uc = UserConfigurator()
    machine = Machine(config=uc)
    prob.model.add_subsystem("machine", machine, promotes_inputs=["*"])

    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options["optimizer"] = "SLSQP"
    prob.driver.options["disp"] = True

    recorder = om.SqliteRecorder("cases.sql")
    # attach recorder to the problem
    prob.add_recorder(recorder)

    # attach recorder to the driver
    prob.driver.add_recorder(recorder)

    prob.model.add_design_var("coils.Ib TF R_out", lower=1.0, upper=4.5, ref=1.5, units="m")
    prob.model.add_design_var("coils.hhs", lower=1.0, upper=10.0, ref=3.0, units="m")
    prob.model.add_design_var("coils.e_a", lower=1.0, upper=15.0, ref=3.0, units="m")
    prob.model.add_design_var("coils.r_c", lower=1.2, upper=10.0, ref=3.0, units="m")

    prob.model.add_objective("machine.V_enc")
    #
    #    # set constraints
    prob.model.add_constraint("machine.coils.constraint_axis_within_coils", lower=3)

    prob.setup(force_alloc_complex=True)
    #
    prob.set_val("R0", 6.0, units="m")
    prob.set_val("plasma.A", 2.4)
    prob.set_val("plasma.κ", 1.9)
    prob.set_val("plasma.δ", 1.0)
    prob.set_val("plasma.ξ", 0.0)
    prob.set_val("offset", 1.5)

    # initial values
 #   prob.set_val("coils.hhs", 5.0, units="m")
 #   prob.set_val("coils.r_c", 4.0, units="m")
    prob.set_val("coils.e_a", 10, units="m")
 #   prob.set_val("coils.Ib TF R_out", 1.2, units="m")

    # add recorder to the objective
    # obj_cmp = prob.model.obj_cmp
    # obj_cmp.add_recorder(recorder)

    # add recorder to the solver
    # prob.model.cycle.add_recorder(recorder)

    prob.run_driver()

    #    all_inputs = prob.model.list_inputs(values=True, print_arrays=True)
    all_outputs = prob.model.list_outputs(values=True, print_arrays=True)

    # plot resulting points
    coil_d_sq = prob.get_val("machine.coils.d_sq")
    coil_theta = prob.get_val("machine.coils.θ")
    coil_d = np.sqrt(coil_d_sq)
    coil_R = prob.get_val("R0") + coil_d * np.cos(coil_theta)
    coil_Z = coil_d * np.sin(coil_theta)

    blanket_d_sq = prob.get_val("machine.plasma.blanket envelope d_sq")
    blanket_theta = prob.get_val("machine.plasma.blanket envelope θ")
    blanket_d = np.sqrt(blanket_d_sq)
    blanket_R = prob.get_val("R0") + blanket_d * np.cos(blanket_theta)
    blanket_Z = blanket_d * np.sin(blanket_theta)

    fig, ax = plt.subplots()
    machine.plasma.geom.plot(ax)
    machine.plasma.bl_pts.plot(ax)
    machine.coils.plot(ax)
    ax.plot(coil_R, coil_Z, marker="o")
    ax.plot(blanket_R, blanket_Z, marker="x")
    ax.set_xlim([-1,8])
    ax.axis('equal')
    plt.show()
