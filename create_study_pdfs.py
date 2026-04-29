from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

Path("data/pdfs").mkdir(parents=True, exist_ok=True)

# ─── PDF 1: JEE Physics ───────────────────────────────────────
c = canvas.Canvas("data/pdfs/jee_physics.pdf", pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 750, "JEE Physics - Complete Study Notes")
c.setFont("Helvetica", 11)

physics_content = [
    "",
    "LAWS OF MOTION",
    "Newtons First Law: An object at rest stays at rest and an object in motion",
    "stays in motion unless acted upon by an unbalanced external force.",
    "This is the law of inertia.",
    "",
    "Newtons Second Law: The net force on an object equals mass times acceleration.",
    "Formula: F = ma, where F is force in Newtons, m is mass in kg,",
    "a is acceleration in m/s squared. In vector form: F vector = m times a vector.",
    "If mass is constant, F = dp/dt where p is momentum.",
    "",
    "Newtons Third Law: For every action there is an equal and opposite reaction.",
    "Forces always occur in pairs. If A exerts force on B, B exerts equal and",
    "opposite force on A. Example: rocket propulsion, swimming, walking.",
    "",
    "WORK, ENERGY AND POWER",
    "Work-Energy Theorem: Work done by net force equals change in kinetic energy.",
    "W = delta KE = half mv squared minus half mu squared.",
    "Work done W = F times d times cos(theta) where theta is angle between F and d.",
    "",
    "Conservation of Energy: Energy cannot be created or destroyed.",
    "Total mechanical energy = Kinetic Energy + Potential Energy = constant.",
    "KE = half mv squared. PE (gravitational) = mgh. PE (spring) = half kx squared.",
    "",
    "Power: Rate of doing work. P = W/t = F times v. Unit: Watt.",
    "",
    "WAVES AND OSCILLATIONS",
    "Simple Harmonic Motion: Restoring force proportional to displacement.",
    "Equation: x = A sin(wt + phi). Period T = 2pi sqrt(m/k).",
    "Frequency f = 1/T. Angular frequency w = 2pi f = sqrt(k/m).",
    "",
    "Principle of Superposition: When waves overlap, resultant displacement",
    "is algebraic sum of individual displacements.",
    "Constructive interference: waves in phase, amplitude adds.",
    "Destructive interference: waves out of phase, amplitude cancels.",
    "",
    "Bernoullis Principle: For streamlined fluid flow,",
    "P + half rho v squared + rho g h = constant.",
    "Faster flow means lower pressure. Applications: aircraft wings, carburetors.",
    "",
    "ELECTROSTATICS",
    "Coulombs Law: F = k q1 q2 / r squared.",
    "k = 9 times 10 to the power 9 Nm squared per C squared.",
    "Force is attractive for unlike charges, repulsive for like charges.",
    "Electric field E = F/q = k Q / r squared.",
    "",
    "Ohms Law: V = IR where V is voltage, I is current, R is resistance.",
    "Limitations: does not apply to semiconductors, electrolytes,",
    "vacuum tubes, thermistors. These are non-ohmic conductors.",
    "Resistance R = rho L / A where rho is resistivity.",
    "",
    "MODERN PHYSICS",
    "Photoelectric Effect: Emission of electrons when light hits metal surface.",
    "Minimum frequency needed is threshold frequency. E = hf where h is Planck constant.",
    "Einstein explained using photon theory. Kinetic energy = hf minus work function.",
    "No emission below threshold frequency regardless of intensity.",
    "",
    "Heisenberg Uncertainty Principle: Cannot simultaneously measure",
    "position and momentum with perfect accuracy.",
    "delta x times delta p >= h divided by 4pi.",
    "Similarly delta E times delta t >= h divided by 4pi.",
    "This is a fundamental property of quantum mechanics, not a measurement error.",
]

y = 720
for line in physics_content:
    if y < 60:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = 750
    c.drawString(50, y, line)
    y -= 16

c.save()
print("Created jee_physics.pdf")

# ─── PDF 2: JEE Chemistry ─────────────────────────────────────
c = canvas.Canvas("data/pdfs/jee_chemistry.pdf", pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 750, "JEE Chemistry - Complete Study Notes")
c.setFont("Helvetica", 11)

chemistry_content = [
    "",
    "ATOMIC STRUCTURE",
    "Avogadros Number: 6.022 times 10 to the power 23 particles per mole.",
    "It represents number of atoms molecules or ions in one mole of substance.",
    "One mole of any gas at STP occupies 22.4 litres.",
    "",
    "Aufbau Principle: Electrons fill orbitals in order of increasing energy.",
    "Order: 1s 2s 2p 3s 3p 4s 3d 4p 5s 4d 5p 6s 4f 5d 6p.",
    "Each orbital holds maximum two electrons with opposite spins (Pauli principle).",
    "",
    "Hunds Rule: Electrons occupy each orbital singly before pairing.",
    "All singly occupied orbitals have electrons with same spin.",
    "This minimizes electron repulsion and gives most stable configuration.",
    "Example: Carbon has 2 unpaired electrons in 2p orbitals.",
    "",
    "Electronegativity: Tendency of atom to attract shared electrons.",
    "Increases across period left to right as nuclear charge increases.",
    "Decreases down group as atomic radius increases.",
    "Fluorine has highest electronegativity of 4.0 on Pauling scale.",
    "Francium has lowest electronegativity.",
    "",
    "CHEMICAL BONDING",
    "Ionic Bond: Complete transfer of electrons between metal and nonmetal.",
    "Creates oppositely charged ions. High melting point. Conducts when dissolved.",
    "Example: NaCl, MgO, CaCl2.",
    "",
    "Covalent Bond: Sharing of electrons between nonmetals.",
    "Single bond shares 2 electrons, double bond 4, triple bond 6.",
    "Generally lower melting points than ionic compounds.",
    "Example: H2O, CO2, CH4.",
    "",
    "Hybridization: Mixing of atomic orbitals to form hybrid orbitals.",
    "sp3: one s and three p orbitals, tetrahedral, 109.5 degrees. Example: CH4.",
    "sp2: one s and two p orbitals, trigonal planar, 120 degrees. Example: C2H4.",
    "sp: one s and one p orbital, linear, 180 degrees. Example: C2H2.",
    "",
    "THERMODYNAMICS",
    "First Law: Energy cannot be created or destroyed.",
    "delta U = Q minus W. U is internal energy, Q is heat added, W is work done by system.",
    "",
    "EQUILIBRIUM",
    "Le Chateliers Principle: If equilibrium system is disturbed, it shifts to",
    "counteract the change and restore equilibrium.",
    "Increase concentration of reactant: equilibrium shifts to products.",
    "Increase temperature: shifts toward endothermic direction.",
    "Increase pressure: shifts toward fewer moles of gas.",
    "",
    "Raoults Law: Partial vapor pressure of component in ideal solution equals",
    "vapor pressure of pure component multiplied by its mole fraction.",
    "P_A = P_A(pure) times x_A. Total pressure = sum of partial pressures.",
    "Positive deviation: interactions between unlike molecules weaker than like.",
    "Negative deviation: interactions between unlike molecules stronger than like.",
    "",
    "ORGANIC CHEMISTRY",
    "SN1 Reaction: Two step. Leaving group departs first forming carbocation,",
    "then nucleophile attacks. Favored by tertiary substrates and polar protic solvents.",
    "Racemization occurs. Rate depends only on substrate concentration.",
    "",
    "SN2 Reaction: One step. Nucleophile attacks as leaving group departs simultaneously.",
    "Favored by primary substrates and polar aprotic solvents.",
    "Inversion of configuration occurs (Walden inversion).",
    "Rate depends on both substrate and nucleophile concentrations.",
]

y = 720
for line in chemistry_content:
    if y < 60:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = 750
    c.drawString(50, y, line)
    y -= 16

c.save()
print("Created jee_chemistry.pdf")

# ─── PDF 3: JEE Mathematics ───────────────────────────────────
c = canvas.Canvas("data/pdfs/jee_math.pdf", pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 750, "JEE Mathematics - Complete Study Notes")
c.setFont("Helvetica", 11)

math_content = [
    "",
    "ALGEBRA",
    "Quadratic Formula: For ax squared + bx + c = 0,",
    "x = (-b plus or minus sqrt(b squared - 4ac)) divided by 2a.",
    "Discriminant D = b squared - 4ac.",
    "D > 0: two distinct real roots. D = 0: one repeated real root.",
    "D < 0: two complex conjugate roots.",
    "",
    "Binomial Theorem: (a+b) to the power n = sum from k=0 to n of C(n,k) a to (n-k) b to k.",
    "General term T(r+1) = C(n,r) times a to (n-r) times b to r.",
    "C(n,r) = n factorial divided by (r factorial times (n-r) factorial).",
    "",
    "CALCULUS",
    "Limit: lim f(x) as x approaches a equals L if f(x) approaches L as x approaches a.",
    "Continuity at x=a requires: f(a) defined, limit exists, limit equals f(a).",
    "If any condition fails the function is discontinuous at that point.",
    "",
    "Fundamental Theorem of Calculus:",
    "Part 1: If F is antiderivative of f, then integral from a to b of f(x)dx = F(b) - F(a).",
    "Part 2: d/dx of integral from a to x of f(t)dt = f(x).",
    "Connects differentiation and integration as inverse operations.",
    "",
    "VECTORS",
    "Dot Product: A dot B = magnitude A times magnitude B times cos(theta).",
    "Result is a scalar. Dot product is zero for perpendicular vectors.",
    "A dot B = Ax*Bx + Ay*By + Az*Bz.",
    "",
    "Cross Product: A cross B = magnitude A times magnitude B times sin(theta) times n hat.",
    "Result is a vector perpendicular to both A and B.",
    "Magnitude equals area of parallelogram formed by the vectors.",
    "Cross product is zero for parallel vectors.",
    "A cross B = (AyBz-AzBy)i + (AzBx-AxBz)j + (AxBy-AyBx)k.",
]

y = 720
for line in math_content:
    if y < 60:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = 750
    c.drawString(50, y, line)
    y -= 16

c.save()
print("Created jee_math.pdf")

# ─── PDF 4: UPSC Polity & History & Economics ─────────────────
c = canvas.Canvas("data/pdfs/upsc_content.pdf", pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 750, "UPSC - Polity, History and Economics Notes")
c.setFont("Helvetica", 11)

upsc_content = [
    "",
    "INDIAN CONSTITUTION - POLITY",
    "Preamble: WE THE PEOPLE OF INDIA solemnly resolve to constitute India into",
    "a SOVEREIGN SOCIALIST SECULAR DEMOCRATIC REPUBLIC.",
    "Secures JUSTICE social economic political.",
    "LIBERTY of thought expression belief faith worship.",
    "EQUALITY of status and opportunity.",
    "FRATERNITY assuring dignity of individual and unity of nation.",
    "Socialist and Secular added by 42nd Amendment 1976.",
    "Preamble is not justiciable but guides interpretation of Constitution.",
    "",
    "Fundamental Rights: Part III Articles 12 to 35. Justiciable rights.",
    "Right to Equality Articles 14 to 18: equality before law, no discrimination",
    "on grounds of religion race caste sex place of birth, abolition of untouchability.",
    "Right to Freedom Articles 19 to 22: freedom of speech expression assembly",
    "association movement residence profession. Protection against arbitrary arrest.",
    "Right against Exploitation Articles 23 to 24: prohibition of human trafficking",
    "and forced labour. No child labour below 14 years in hazardous employment.",
    "Right to Freedom of Religion Articles 25 to 28: freedom of conscience",
    "and free profession practice propagation of religion.",
    "Cultural and Educational Rights Articles 29 to 30: minorities right to",
    "conserve culture and establish educational institutions.",
    "Right to Constitutional Remedies Article 32: right to move Supreme Court",
    "for enforcement of fundamental rights. Writs: habeas corpus mandamus",
    "prohibition certiorari quo warranto.",
    "",
    "Directive Principles: Part IV Articles 36 to 51. Non-justiciable.",
    "Guidelines for state policy to promote social and economic justice.",
    "Include: equal pay for equal work, free legal aid, living wage,",
    "uniform civil code, protection of environment, free education up to 14 years.",
    "Cannot be enforced by courts but fundamental in governance.",
    "",
    "Federal Structure: Union List 97 subjects Parliament legislates.",
    "State List 66 subjects State legislates.",
    "Concurrent List 47 subjects both legislate Union prevails on conflict.",
    "Residuary powers with Union. Governor represents Centre in states.",
    "India described as quasi-federal with strong centre.",
    "",
    "Judicial Review: Power of courts to examine constitutionality of laws.",
    "Article 13: laws inconsistent with Fundamental Rights are void.",
    "Supreme Court under Article 32 enforces fundamental rights.",
    "High Courts under Article 226 issue writs.",
    "Basic structure doctrine from Kesavananda Bharati case 1973.",
    "Parliament cannot amend basic structure of Constitution.",
    "",
    "INDIAN HISTORY",
    "1857 Revolt Causes:",
    "Political: Doctrine of Lapse by Dalhousie, annexation of Awadh.",
    "Economic: drain of wealth, destruction of Indian industries, heavy taxation.",
    "Social: interference with customs, Western education imposition.",
    "Military: racial discrimination, greased cartridges with Enfield rifle.",
    "Religious: fear of forced conversion by missionaries.",
    "Started at Meerut on May 10 1857. Suppressed by 1858.",
    "",
    "Dandi March 1930: Gandhi led 241-mile march from Sabarmati to Dandi.",
    "Protested British salt tax. Launched Civil Disobedience Movement.",
    "First major nonviolent mass movement. Internationalized freedom struggle.",
    "Demonstrated ordinary people could challenge colonial authority.",
    "Led to mass arrests including Gandhi.",
    "",
    "Rowlatt Act 1919: Allowed imprisonment without trial for up to two years.",
    "Suspended civil liberties. No right of appeal.",
    "Triggered mass protests across India.",
    "Led to Jallianwala Bagh massacre on April 13 1919.",
    "General Dyer ordered firing on peaceful crowd. 379 killed officially.",
    "",
    "ECONOMICS",
    "GDP: Gross Domestic Product is total monetary value of all final goods",
    "and services produced within country borders in specific time period.",
    "Three methods: Expenditure method GDP = C + I + G + NX.",
    "Income method: sum of all factor incomes.",
    "Production method: sum of value added at each stage.",
    "India uses GDP at market prices and GDP at factor cost.",
    "",
    "Inflation: Sustained increase in general price level.",
    "Demand-pull: excess demand over supply.",
    "Cost-push: rising production costs passed to consumers.",
    "Built-in: wage-price spiral.",
    "Measured by CPI Consumer Price Index and WPI Wholesale Price Index.",
    "RBI targets CPI inflation at 4 percent with 2 percent tolerance band.",
    "",
    "Fiscal Deficit: Total government expenditure minus total revenue receipts",
    "excluding borrowings.",
    "Fiscal deficit = Total expenditure minus (Revenue receipts + Non-debt capital receipts).",
    "Indicates amount government needs to borrow.",
    "FRBM Act targets fiscal deficit at 3 percent of GDP.",
    "High fiscal deficit leads to inflation and crowding out of private investment.",
]

y = 720
for line in upsc_content:
    if y < 60:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = 750
    c.drawString(50, y, line)
    y -= 16

c.save()
print("Created upsc_content.pdf")
print("All PDFs created successfully.")
