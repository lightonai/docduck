"""Static pools that don't fit the per-block defaults dict.

Everything block- or chrome-related has moved into `defaults.py`. Two
collections remain here because they're indexed structures (not flat
floats/strings) consumed at render time:

- MATH_EQUATIONS_MULTILINE: lists of LaTeX lines, used by the math block
  when `multiline_probability` fires.
- TABLE_HEADERS_POOL: realistic header rows for the structured-content
  text generator.
"""

MATH_EQUATIONS_MULTILINE = [
    # Maxwell's equations
    [
        r"\nabla \cdot \mathbf{E} = \frac{\rho}{\varepsilon_0}",
        r"\nabla \cdot \mathbf{B} = 0",
        r"\nabla \times \mathbf{E} = -\frac{\partial \mathbf{B}}{\partial t}",
        r"\nabla \times \mathbf{B} = \mu_0 \mathbf{J} + \mu_0 \varepsilon_0 \frac{\partial \mathbf{E}}{\partial t}",
    ],
    # Thermodynamic potentials
    [
        r"dU = T\,dS - P\,dV",
        r"dH = T\,dS + V\,dP",
        r"dF = -S\,dT - P\,dV",
        r"dG = -S\,dT + V\,dP",
    ],
    # Euler-Lagrange + Hamilton
    [
        r"\frac{d}{dt}\frac{\partial L}{\partial \dot{q}} - \frac{\partial L}{\partial q} = 0",
        r"H = \sum_i p_i \dot{q}_i - L",
    ],
    # Gradient, divergence, curl in spherical
    [
        r"\nabla f = \frac{\partial f}{\partial r}\hat{r} + \frac{1}{r}\frac{\partial f}{\partial \theta}\hat{\theta}",
        r"\nabla \cdot \mathbf{A} = \frac{1}{r^2}\frac{\partial}{\partial r}(r^2 A_r) + \frac{1}{r\sin\theta}\frac{\partial}{\partial \theta}(\sin\theta \, A_\theta)",
    ],
    # Navier-Stokes (two lines)
    [
        r"\rho\left(\frac{\partial \mathbf{v}}{\partial t} + \mathbf{v} \cdot \nabla \mathbf{v}\right) =",
        r"-\nabla p + \mu \nabla^2 \mathbf{v} + \mathbf{f}",
    ],
    # Fourier series
    [
        r"f(x) = \frac{a_0}{2} + \sum_{n=1}^{\infty} \left(a_n \cos\frac{n\pi x}{L} + b_n \sin\frac{n\pi x}{L}\right)",
        r"a_n = \frac{1}{L}\int_{-L}^{L} f(x)\cos\frac{n\pi x}{L}\,dx",
    ],
    # Logistic regression
    [
        r"\sigma(z) = \frac{1}{1 + e^{-z}}",
        r"J(\theta) = -\frac{1}{m}\sum_{i=1}^{m}\left[y^{(i)}\log h_\theta(x^{(i)}) + (1-y^{(i)})\log(1-h_\theta(x^{(i)}))\right]",
    ],
]

TABLE_HEADERS_POOL = [
    ["Year", "Population", "Growth (%)", "GDP ($B)"],
    ["Model", "Accuracy", "F1 Score", "Latency (ms)"],
    ["City", "Temperature (°C)", "Humidity (%)", "Wind (km/h)"],
    ["Element", "Symbol", "Atomic No.", "Weight (u)"],
    ["Parameter", "Value", "Std. Error", "p-value"],
    ["Country", "Area (km²)", "Population", "Density"],
    ["Drug", "Dose (mg)", "Efficacy (%)", "Side Effects"],
    ["Wavelength (nm)", "Frequency (THz)", "Energy (eV)", "Color"],
]
