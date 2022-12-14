import openmdao.api as om
from faroes.configurator import UserConfigurator
from scipy.constants import mu_0, mega, kilo


class BetaNTotal(om.ExplicitComponent):
    r"""Total β_N from a scaling law and a multiplier

    Inputs
    ------
    A : float
        Aspect ratio
    f : float
        A multiplier to β_N. The default is set via configuration.

    Outputs
    -------
    β_N : float
        normalized beta from a scaling law

    β_N total : float
        the actual normalized beta

    Reference
    ---------
    Physics of Plasmas 11, 639 (2004);
    https://doi.org/10.1063/1.1640623

    No-wall limit, with 50% bootstrap fraction
    """
    def initialize(self):
        self.options.declare('config', default=None, recordable=False)

    def setup(self):
        if self.options['config'] is not None:
            self.config = self.options['config']
            ac = self.config.accessor(['fits'])
            self.β_ε_scaling_constants = ac(
                ["no-wall β_N scaling with ε", "constants"])
            β_N_multiplier = ac(["β_N multiplier"])
        else:
            β_N_multiplier = 1

        self.add_input("A", desc="Aspect Ratio")
        self.add_input("f", val=β_N_multiplier, desc="Fraction of maximum β_N")
        self.add_output("β_N", units="m * T / MA", desc="Normalized beta")
        self.add_output("β_N total",
                        units="m * T / MA",
                        desc="Normalized beta, total")

    def β_N_scaling(self, A):
        """Estimated β_N from A

        Parameters
        ----------
        A: float
            aspect ratio of the plasma

        Returns
        -------
        β_N : float
            Normalized total pressure
            Fractional, not %.

        """
        const = self.β_ε_scaling_constants
        b = const[0]
        c = const[1]
        d = const[2]
        return (b + c / (A**d)) / 100

    def compute(self, inputs, outputs):
        A = inputs["A"]
        β_N_law = self.β_N_scaling(A)
        outputs["β_N"] = β_N_law
        outputs["β_N total"] = β_N_law * inputs["f"]

    def setup_partials(self):
        self.declare_partials(["β_N", "β_N total"], ["A", "f"])

    def compute_partials(self, inputs, J):
        const = self.β_ε_scaling_constants
        A = inputs["A"]
        β_N_law = self.β_N_scaling(A)
        c = const[1]
        d = const[2]
        J["β_N", "A"] = -0.01 * A**(-d - 1) * c * d
        scale = inputs["f"]
        J["β_N total", "A"] = scale * J["β_N", "A"]
        J["β_N total", "f"] = β_N_law


class BetaToroidal(om.ExplicitComponent):
    r"""Toroidal beta, from β_N total

    This is a "specified" βt.

    It acts as part of a goal for adjusting the H-factor.
    BetaN is specified as a function of A according to an empirical fit,
    and <p> is a descendent of that (through this βt).
    Another <p> is calculated separately using the confinement time and
    Greenwald density.

    Inputs
    ------
    β_N total : float
        m T / MA, total normalized beta
    Ip : float
        MA, Plasma current
    Bt : float
        T, Vacuum toroidal field at geometric center
    a : float
        m, Minor radius

    Outputs
    -------
    βt : float
        Toroidal beta
    """
    def setup(self):
        self.add_input("Ip", units="MA", desc="Plasma current")
        self.add_input("Bt",
                       units="T",
                       desc="Vacuum toroidal field at geometric center")
        self.add_input("a", units="m", desc="Minor radius")
        self.add_input("β_N total",
                       units="m * T / MA",
                       desc="Total normalized beta")
        βt_ref = 0.02
        self.add_output("βt",
                        lower=0,
                        upper=1,
                        ref=βt_ref,
                        desc="Toroidal beta")

    def compute(self, inputs, outputs):
        Ip = inputs["Ip"]
        Bt = inputs["Bt"]
        a = inputs["a"]
        βN_tot = inputs["β_N total"]
        βt = Ip * βN_tot / (Bt * a)
        outputs["βt"] = βt

    def setup_partials(self):
        self.declare_partials(["βt"], ["Ip", "Bt", "a", "β_N total"])

    def compute_partials(self, inputs, J):
        Ip = inputs["Ip"]
        Bt = inputs["Bt"]
        a = inputs["a"]
        βN_tot = inputs["β_N total"]
        J["βt", "Ip"] = βN_tot / (Bt * a)
        J["βt", "β_N total"] = Ip / (Bt * a)
        J["βt", "Bt"] = -Ip * βN_tot / (Bt**2 * a)
        J["βt", "a"] = -Ip * βN_tot / (Bt * a**2)


class SpecifiedTotalAveragePressure(om.ExplicitComponent):
    r"""Total <p> (specified)

    Notes
    -----
    In Menard's model, this is referred to as "specified" because
    it acts as a goal for adjusting the H-factor.
    BetaN is specified as a function of A according to an empirical fit,
    and this <p> is a descendent of that (through βt).
    Another <p> is calculated separately using the confinement time and
    Greenwald density. It gets adjusted to match this one.

    Inputs
    ------
    Bt : float
        T, Vacuum toroidal field on axis
    βt : float
        Toroidal beta
    <(R0/R)^2> : float
        Geometric shaping factor to convert from the vacuum toroidal field
        on-axis to the average vacuum toroidal field within the LCFS.

    Outputs
    -------
    <p_tot> : float
        kPa, Total specified average pressure

    Notes
    -----
    Under the assumption that βt numbers were previously computed using the
    definition <p>/(Bt^2/2μ0) rather than <p>/<Bt^2/2μ0>, and that it was
    typically done with plasmas of low triangularity, it may be useful to
    use a version of <(R0/R)^2> which is normalized to unity for elliptical
    plasmas.
    """
    def setup(self):
        self.add_input("Bt",
                       units="T",
                       desc="Vacuum toroidal field at geometric center")
        self.add_input("βt", desc="Toroidal beta")
        self.add_input("<(R0/R)^2>", val=1, desc="Geometric shaping factor")

        p_ref = 10**5
        self.add_output("<p_tot>",
                        units="kPa",
                        ref=p_ref,
                        lower=0,
                        desc="Volume-averaged total pressure")

    def compute(self, inputs, outputs):
        βt = inputs["βt"]
        Bt = inputs["Bt"]
        f_shaping = inputs["<(R0/R)^2>"]
        p_avg = f_shaping * βt * (Bt**2 / (2 * mu_0))
        outputs["<p_tot>"] = p_avg / kilo

    def setup_partials(self):
        self.declare_partials("<p_tot>", ["βt", "Bt", "<(R0/R)^2>"])

    def compute_partials(self, inputs, J):
        βt = inputs["βt"]
        Bt = inputs["Bt"]
        f_shaping = inputs["<(R0/R)^2>"]
        J["<p_tot>", "βt"] = f_shaping * (Bt**2 / (2 * mu_0)) / kilo
        J["<p_tot>", "Bt"] = f_shaping * βt * Bt / (mu_0) / kilo
        J["<p_tot>", "<(R0/R)^2>"] = βt * (Bt**2 / (2 * mu_0)) / kilo


class BPoloidal(om.ExplicitComponent):
    r"""Average poloidal field over the LCFS

    The average poloidal field on the LCFS is

    .. math::

       B_p = \frac{\mu_0 I_p}{L_\mathrm{pol}}

    where :math:`I_p` is the plasma current and
    :math:`L_\mathrm{pol}` is the poloidal LCFS circumference.

    Inputs
    ------
    Ip : float
        MA, Plasma current (absolute value)
    L_pol : float
        m, Poloidal circumference at LCFS

    Outputs
    -------
    Bp : float
        T, average poloidal field
    """
    def setup(self):
        self.add_input("Ip", units="MA", desc="Plasma current")
        self.add_input("L_pol", units="m", desc="Poloidal circumference")
        Bp_ref = 1
        tiny = 1e-6
        self.add_output("Bp",
                        units="T",
                        ref=Bp_ref,
                        lower=tiny,
                        desc="Average poloidal field at LCFS")

    def compute(self, inputs, outputs):
        Ip = inputs["Ip"]
        L_pol = inputs["L_pol"]
        Bp = mu_0 * mega * Ip / L_pol
        outputs["Bp"] = Bp

    def setup_partials(self):
        self.declare_partials("Bp", ["Ip", "L_pol"])

    def compute_partials(self, inputs, J):
        Ip = inputs["Ip"]
        L_pol = inputs["L_pol"]
        J["Bp", "Ip"] = mu_0 * mega / L_pol
        J["Bp", "L_pol"] = -mu_0 * mega * Ip / L_pol**2


class BetaPoloidal(om.ExplicitComponent):
    r"""Total poloidal beta

    .. math::

       \beta_{p,tot} = 2 \left<p_{tot}\right> (\mu_0 / B_p^2)

    Inputs
    ------
    <p_tot> : float
        kPa, total averaged pressure
    Bp : float
        T, Averaged poloidal field at LCFS

    Outputs
    -------
    βp : float
        Poloidal beta
    """
    def setup(self):
        self.add_input("<p_tot>",
                       units="kPa",
                       desc="Volume-averaged total pressure")
        self.add_input("Bp", units="T", desc="Average poloidal field at LCFS")
        self.add_output("βp", desc="Poloidal beta")

    def compute(self, inputs, outputs):
        Bp = inputs["Bp"]
        p_tot = inputs["<p_tot>"]
        βp = p_tot * kilo * 2 * mu_0 / Bp**2
        outputs["βp"] = βp

    def setup_partials(self):
        self.declare_partials("βp", ["Bp", "<p_tot>"])

    def compute_partials(self, inputs, J):
        Bp = inputs["Bp"]
        p_tot = inputs["<p_tot>"]
        p_tot * kilo * 2 * mu_0 / Bp**2
        J["βp", "Bp"] = -2 * p_tot * kilo * 2 * mu_0 / Bp**3
        J["βp", "<p_tot>"] = kilo * 2 * mu_0 / Bp**2


class SpecifiedPressure(om.Group):
    r"""

    Inputs
    ------
    A : float
        Aspect Ratio
    Bt : float
        T, Vacuum toroidal field
    Ip : float
        MA, plasma current
    a : float
        m, minor radius
    L_pol : float
        m, LCFS perimeter

    Outputs
    -------
    β_N total : float
        the specified total normalized beta
    Bp : float
        T, average poloidal field
    βt : float
        Toroidal beta
    βp : float
        Poloidal beta
    <p_tot> : float
        kPa, Total specified average pressure
    """
    def initialize(self):
        self.options.declare('config', default=None, recordable=False)

    def setup(self):
        config = self.options['config']
        self.add_subsystem("betaNtot",
                           BetaNTotal(config=config),
                           promotes_inputs=["A"])
        self.add_subsystem("beta_t",
                           BetaToroidal(),
                           promotes_inputs=["Ip", "Bt", "a"],
                           promotes_outputs=["βt"])
        self.add_subsystem("p_avg",
                           SpecifiedTotalAveragePressure(),
                           promotes_inputs=["Bt", "βt"])
        self.add_subsystem("B_p",
                           BPoloidal(),
                           promotes_inputs=["Ip", "L_pol"],
                           promotes_outputs=["Bp"])
        self.add_subsystem("beta_p",
                           BetaPoloidal(),
                           promotes_inputs=["Bp"],
                           promotes_outputs=["βp"])
        self.connect("betaNtot.β_N total", ["beta_t.β_N total"])
        self.connect("p_avg.<p_tot>", ["beta_p.<p_tot>"])


class ThermalBetaPoloidal(om.ExplicitComponent):
    r"""Beta_poloidal due to thermal particles only

    Note: this is not part of the above group, but
    it does in practice use some of its outputs.

    Inputs
    ------
    βp : float
        Beta poloidal (total)
    thermal pressure fraction : float
        Fraction of pressure which is from thermal rather than fast particles.

    Outputs
    -------
    βp_th : float
        Thermal poloidal beta
    """
    def setup(self):
        self.add_input("βp", desc="Total poloidal beta")
        self.add_input("thermal pressure fraction",
                       desc="Fraction of pressure from thermal particles")
        self.add_output("βp_th", lower=0, desc="Thermal poloidal beta")

    def compute(self, inputs, outputs):
        βp = inputs["βp"]
        f_th = inputs["thermal pressure fraction"]
        βp_th = βp * f_th
        outputs["βp_th"] = βp_th

    def setup_partials(self):
        self.declare_partials("βp_th", ["βp", "thermal pressure fraction"])

    def compute_partials(self, inputs, J):
        J["βp_th", "βp"] = inputs["thermal pressure fraction"]
        J["βp_th", "thermal pressure fraction"] = inputs["βp"]


if __name__ == "__main__":
    prob = om.Problem()
    uc = UserConfigurator()

    prob.model = SpecifiedPressure(config=uc)

    prob.setup()

    prob.set_val('A', 1.6)
    prob.set_val('a', 1.875)
    prob.set_val('Ip', 14, units="MA")
    prob.set_val('Bt', 2, units="T")
    prob.set_val('L_pol', 20, units="m")

    prob.run_driver()
    prob.model.list_inputs(units=True, desc=True)
    prob.model.list_outputs(units=True, desc=True)
