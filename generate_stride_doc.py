import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """Sets background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    """Sets padding for table cell in twips."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def build_complete_academic_document():
    doc = Document()

    # Color Palette
    NAVY = RGBColor(27, 54, 93)       # Primary #1B365D
    STEEL = RGBColor(75, 107, 148)    # Secondary #4B6B94
    CHARCOAL = RGBColor(40, 40, 40)   # Body text #282828
    RED_ACCENT = RGBColor(180, 40, 40)
    GREEN_ACCENT = RGBColor(30, 130, 60)
    AMBER_ACCENT = RGBColor(190, 110, 0)
    PURPLE_ACCENT = RGBColor(120, 40, 140)

    # Page Margins (1 inch all around)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = CHARCOAL

    # Header / Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    run_sub = title_p.add_run("SOFTWARE SYSTEMS ENGINEERING (SSE) • LAB DELIVERABLE • PHASES 5, 6, 7 & 8\n")
    run_sub.font.size = Pt(9.5)
    run_sub.font.bold = True
    run_sub.font.color.rgb = STEEL

    run_title = title_p.add_run("Software Systems Engineering: Comprehensive Report\nThreat Modeling, Attack Trees, UI Design & Product Backlog")
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = NAVY

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(4)
    p_meta.paragraph_format.space_after = Pt(16)
    run_meta = p_meta.add_run(
        "Project: Quantum-Safe Hybrid VPN Testbed with Real-Time Shor's Cryptanalytic Attack Demonstration\n"
        "Cryptographic Standards: NIST FIPS 203 (ML-KEM-768), RFC 3526 MODP, RFC 1928 (SOCKS5), AES-256-GCM\n"
        "Coverage: Phase 5 (Exercises 6, 7, 8, 9) + Phase 6 (Exercise 10) + Phase 7 (Exercise 11) + Phase 8 (Exercise 12)\n"
        "Date of Submission: October 2026 | Document Status: Complete & Verified"
    )
    run_meta.font.size = Pt(9.0)
    run_meta.font.italic = True
    run_meta.font.color.rgb = STEEL

    # Callout Box: Scope
    callout = doc.add_table(rows=1, cols=1)
    callout.alignment = WD_TABLE_ALIGNMENT.CENTER
    callout.autofit = False
    c_cell = callout.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, "F0F4F8")
    set_cell_margins(c_cell, top=130, bottom=130, left=180, right=180)

    cp = c_cell.paragraphs[0]
    cp.paragraph_format.space_after = Pt(3)
    c_head = cp.add_run("COMPREHENSIVE SSE ENGINEERING REPORT OVERVIEW\n")
    c_head.font.bold = True
    c_head.font.size = Pt(10)
    c_head.font.color.rgb = NAVY

    scope_text = (
        "This master document consolidates all core analytical and design deliverables for the Quantum-Safe Hybrid VPN Testbed:\n"
        "• Phase 5 – Threat Modeling: Exercise 6 (Asset & CIA Triad Analysis), Exercise 7 (STRIDE Threat Matrix), "
        "Exercise 8 (Information Flow Analysis), Exercise 9 (Vulnerability Analysis Table).\n"
        "• Phase 6 – Attack Tree: Exercise 10 (Root Goal, AND/OR Boolean Decomposition, 8 Attack Paths, Feasibility Analysis).\n"
        "• Phase 7 – UI Design: Exercise 11 (3 Major Screen Designs, Golden Rules of UI, Navigation, Input, Error Handling).\n"
        "• Phase 8 – Product Backlog: Exercise 12 (10 Comprehensive User Stories in Agile Format with Epics & MoSCoW Priorities)."
    )
    c_body = cp.add_run(scope_text)
    c_body.font.size = Pt(9.5)
    c_body.font.color.rgb = CHARCOAL

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ==========================================
    # SECTION 1: EXERCISE 6 - IDENTIFY ASSETS
    # ==========================================
    doc.add_heading("1. Phase 5 – Exercise 6: Asset Identification and CIA Analysis", level=1)
    p_ex6 = doc.add_paragraph(
        "Asset identification establishes the core inventory of digital, cryptographic, and operational resources "
        "managed by the Quantum-Safe VPN system. Each asset is evaluated against the classic CIA Triad (Confidentiality, "
        "Integrity, Availability) to determine its criticality rating and protective requirements."
    )
    p_ex6.paragraph_format.space_after = Pt(8)

    asset_table = doc.add_table(rows=1, cols=6)
    asset_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    a_hdr = asset_table.rows[0].cells
    a_hdr[0].width = Inches(0.7)
    a_hdr[1].width = Inches(1.3)
    a_hdr[2].width = Inches(1.8)
    a_hdr[3].width = Inches(0.9)
    a_hdr[4].width = Inches(0.8)
    a_hdr[5].width = Inches(1.0)

    a_titles = ["ID", "Asset Name", "Technical Representation", "CIA Needs", "Rating", "Security Rationale"]
    for i, title in enumerate(a_titles):
        set_cell_background(a_hdr[i], "1B365D")
        set_cell_margins(a_hdr[i], top=100, bottom=100, left=80, right=80)
        p = a_hdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(255, 255, 255)

    assets_data = [
        ("A-01", "Ephemeral Private Keys", "DH-16 private exponent (a, b), DH-2048 private key, and NIST ML-KEM-768 lattice secret vector s in RAM.", "C: Critical\nI: Critical\nA: High", "CRITICAL", "Compromise of private keys permits total derivation of shared secrets and full tunnel decryption."),
        ("A-02", "Symmetric Session Keys & Nonces", "256-bit symmetric key derived via HKDF-SHA256, 96-bit AES-GCM IVs, and MAC state.", "C: Critical\nI: Critical\nA: High", "CRITICAL", "Active session keys protect all in-flight application data; key alteration desynchronizes tunnel."),
        ("A-03", "Cleartext Application Payloads", "HTTP/HTTPS request bodies, streaming media chunks (Netflix video frames), auth cookies, and form tokens.", "C: High\nI: High\nA: High", "HIGH", "User personal data and credentials must remain private from public Wi-Fi eavesdroppers."),
        ("A-04", "DNS Queries & Target Hostnames", "Domain names requested by client browser, transmitted via SOCKS5 byte 0x03 to cloud gateway.", "C: High\nI: Critical\nA: High", "HIGH", "DNS queries expose user browsing habits and metadata. Poisoning leads to phishing redirection."),
        ("A-05", "Cloud Gateway Sockets & Service", "Listening WebSocket server on Port 443, async event loop, and outbound TCP sockets in cloud_server.py.", "C: Low\nI: High\nA: Critical", "HIGH", "Service uptime is paramount; socket exhaustion or process crashes sever all active VPN connections."),
        ("A-06", "System Proxy Registry Settings", "Windows Registry keys: ProxyServer ('socks=127.0.0.1:1080') and ProxyEnable in HKCU.", "C: Low\nI: High\nA: High", "MEDIUM", "Corrupted registry values break host internet access or redirect traffic to rogue local proxies."),
        ("A-07", "Cryptanalytic Attack Telemetry", "Benchmark logs, Shor algorithm execution times (0.13 ms), recovered private keys, and decrypted bytes.", "C: Medium\nI: High\nA: Medium", "MEDIUM", "Academic proof of Shor's quantum break. Tampering invalidates experimental evaluation and viva demo."),
        ("A-08", "Active Stream Multiplexer Table", "Dynamic in-memory hash map linking 32-bit stream IDs to client loopback sockets and remote sockets.", "C: Medium\nI: Critical\nA: Critical", "HIGH", "Mapping integrity prevents cross-talk where packets from one browser tab are misrouted to another.")
    ]

    for row_idx, (aid, aname, adesc, acia, arate, arat) in enumerate(assets_data):
        row = asset_table.add_row()
        cells = row.cells
        cells[0].width = Inches(0.7)
        cells[1].width = Inches(1.3)
        cells[2].width = Inches(1.8)
        cells[3].width = Inches(0.9)
        cells[4].width = Inches(0.8)
        cells[5].width = Inches(1.0)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([aid, aname, adesc, acia, arate, arat]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=70, right=70)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 1: r.font.bold = True
            elif i == 4 and "CRITICAL" in val: r.font.bold = True; r.font.color.rgb = RED_ACCENT
            elif i == 4 and "HIGH" in val: r.font.bold = True; r.font.color.rgb = AMBER_ACCENT

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 2: EXERCISE 7 - STRIDE THREAT ANALYSIS
    # ==========================================
    doc.add_heading("2. Phase 5 – Exercise 7: STRIDE Threat Analysis", level=1)
    p_ex7 = doc.add_paragraph(
        "STRIDE threat modeling applies the six core threat categories across the processes, data flows, and data stores "
        "defined in the system DFD. Twelve (12) comprehensive threats are analyzed below to provide exhaustive coverage."
    )
    p_ex7.paragraph_format.space_after = Pt(8)

    stride_table = doc.add_table(rows=1, cols=6)
    stride_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    s_hdr = stride_table.rows[0].cells
    s_hdr[0].width = Inches(0.7)
    s_hdr[1].width = Inches(1.1)
    s_hdr[2].width = Inches(1.1)
    s_hdr[3].width = Inches(1.5)
    s_hdr[4].width = Inches(1.0)
    s_hdr[5].width = Inches(1.6)

    col_titles = ["ID", "DFD Element", "STRIDE Category", "Threat Scenario", "Impact & Risk", "Engineering Mitigation"]
    for i, title in enumerate(col_titles):
        set_cell_background(s_hdr[i], "1B365D")
        set_cell_margins(s_hdr[i], top=100, bottom=100, left=80, right=80)
        p = s_hdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(255, 255, 255)

    threats = [
        ("T-01", "Process P5\n(Cloud Gateway)", "Spoofing\n(Identity)", "Rogue Gateway Impersonation: Adversary deploys a rogue server on public Wi-Fi or poisons DNS to impersonate the Codespaces cloud gateway.", "CRITICAL\nInterception of tunnel handshakes; victim traffic diversion.", "TLS 1.3 encapsulation over Port 443 with certificate validation; out-of-band server public identity verification; NIST ML-KEM decapsulation authenticity."),
        ("T-02", "Process P1\n(Local Proxy)", "Spoofing\n(Port Hijack)", "Loopback Port Hijacking: A rogue unprivileged process binds to 127.0.0.1:1080 before VPN client launch, hijacking browser requests.", "HIGH\nCleartext browser requests redirected to malicious local agent.", "SO_EXCLUSIVEADDRUSE socket option enforced on Windows; process validates loopback ownership prior to routing."),
        ("T-03", "Data Flow DF3\n(Tunnel Frames)", "Tampering\n(Packet Injection)", "In-Transit Ciphertext Bit-Flipping: Active adversary on transit WAN flips bits or injects malformed frames into encrypted WebSocket streams.", "HIGH\nCorrupted stream data or session desynchronization.", "AES-256-GCM AEAD: 128-bit authentication tag verified per frame. Tampered frames immediately trigger an authentication error and close stream."),
        ("T-04", "Data Store DS4\n(Windows Registry)", "Tampering\n(Registry Injection)", "System Proxy Registry Manipulation: Host malware modifies ProxyServer or ProxyEnable keys in HKCU to redirect traffic away from 127.0.0.1:1080.", "MEDIUM\nBypasses tunnel; leaks traffic directly over unsecured Wi-Fi.", "Client reads and enforces registry state continuously; automatic registry flush and restore on GUI shutdown (wininet.dll InternetSetOptionW)."),
        ("T-05", "Data Flow DF2\n(Handshake)", "Repudiation\n(Session Denial)", "Handshake Sequence Replay: Adversary replays past handshake negotiation frames, attempting to re-establish or forge prior sessions.", "LOW\nAmbiguity in connection provenance and session attribution.", "Cryptographic per-session nonces, ephemeral public key exchange (PFS), and monotonic frame sequence counters."),
        ("T-06", "Data Flow DF2\n(Handshake)", "Information Disclosure\n(Harvest-Now-Decrypt)", "Quantum Cryptanalysis of Classical DH: Adversary records 16-bit DH handshakes to break via Shor's discrete-log algorithm (y1*a + y2 = 0 mod r).", "CRITICAL\nComplete historical compromise of confidential payloads, browsing data, and credentials.", "NIST FIPS 203 ML-KEM-768: Module-Lattice Key Encapsulation (M-LWE). Computationally immune to Shor's quantum period-finding algorithm."),
        ("T-07", "Process P5\n(DNS Resolver)", "Information Disclosure\n(DNS Leak)", "Local DNS Query Leakage: User applications bypass the tunnel for host resolution, transmitting cleartext DNS requests over UDP 53 to local ISP/router.", "HIGH\nExposes visited websites and domain metadata to local eavesdroppers.", "Remote DNS Resolution: SOCKS5 protocol byte 0x03 (domain name) encapsulates hostnames; DNS is resolved strictly at Cloud Exit Node."),
        ("T-08", "Data Store DS2\n(Key Cache)", "Information Disclosure\n(Memory Scraping)", "Ephemeral Key Residual Memory Exposure: Unencrypted AES-256 session keys remain resident in volatile RAM after session disconnect.", "HIGH\nPost-mortem exposure of session keys via memory dumps or crash logs.", "Cryptographic Zeroization: Ephemeral key buffers explicitly overwritten with random/zeroed bytes upon session disconnect; explicit garbage collection."),
        ("T-09", "Process P5\n(Cloud Gateway)", "Denial of Service\n(Socket Flooding)", "WebSocket Syn-Flood: Flooding port 443 with incomplete handshakes exhausts file descriptors and worker threads.", "HIGH\nService starvation for legitimate connecting clients.", "Asynchronous non-blocking architecture, per-IP connection limits, and strict 10-second handshake timeout."),
        ("T-10", "Process P4\n(Shor Simulator)", "Denial of Service\n(CPU Starvation)", "Cryptanalytic CPU Starvation: Invoking Shor's order finding on large integers locks Python's GIL and freezes the client GUI.", "MEDIUM\nGUI becomes unresponsive; client process appears hung.", "Background worker execution via daemon threads; attack limited to educational 16-bit moduli with 5.0s computation timeout."),
        ("T-11", "Process P6\n(TCP Dispatcher)", "Elevation of Privilege\n(SSRF / Cloud Pivot)", "SSRF Pivot via Cloud Egress: Client sends SOCKS5 CONNECT requests targeting internal cloud metadata services (e.g. 169.254.169.254).", "HIGH\nAttacker pivots from VPN proxy into cloud host internal infrastructure.", "Egress IP Filtering: Outbound socket dispatcher blacklists link-local (169.254.0.0/16), loopback (127.0.0.0/8), and internal cloud subnets."),
        ("T-12", "Process P1\n(Windows Client)", "Elevation of Privilege\n(Admin Misuse)", "Privilege Escalation via Registry Writes: Proxy toggling requiring elevated administrator rights creates UAC bypass risks.", "LOW\nUnauthorized privilege escalation or access denial.", "Least-Privilege Operation: Proxy changes execute strictly in user-space (HKEY_CURRENT_USER), requiring zero administrative/root privileges.")
    ]

    for row_idx, (tid, delem, scat, tvec, timpact, tmit) in enumerate(threats):
        row = stride_table.add_row()
        cells = row.cells
        cells[0].width = Inches(0.7)
        cells[1].width = Inches(1.1)
        cells[2].width = Inches(1.1)
        cells[3].width = Inches(1.5)
        cells[4].width = Inches(1.0)
        cells[5].width = Inches(1.6)
        bg_color = "F4F7FB" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([tid, delem, scat, tvec, timpact, tmit]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=70, right=70)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.0)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 2:
                r.font.bold = True
                if "Spoofing" in val: r.font.color.rgb = RGBColor(180, 80, 0)
                elif "Tampering" in val: r.font.color.rgb = RED_ACCENT
                elif "Information" in val: r.font.color.rgb = RED_ACCENT
                elif "Denial" in val: r.font.color.rgb = RGBColor(140, 0, 140)
                elif "Elevation" in val: r.font.color.rgb = RGBColor(0, 100, 160)
            elif i == 4 and "CRITICAL" in val: r.font.bold = True; r.font.color.rgb = RED_ACCENT

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 3: EXERCISE 8 - INFORMATION FLOW ANALYSIS
    # ==========================================
    doc.add_heading("3. Phase 5 – Exercise 8: Information Flow Analysis", level=1)
    p_ex8 = doc.add_paragraph(
        "Information Flow Analysis tracks the movement of sensitive assets across system boundaries, distinguishing "
        "between trusted and untrusted channels, identifying trust boundaries crossed, and exposing potential unauthorized "
        "data flows (leakage vectors) along with the corresponding architectural controls."
    )
    p_ex8.paragraph_format.space_after = Pt(8)

    flow_table = doc.add_table(rows=1, cols=7)
    flow_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    f_hdr = flow_table.rows[0].cells
    f_hdr[0].width = Inches(0.6)
    f_hdr[1].width = Inches(1.0)
    f_hdr[2].width = Inches(1.1)
    f_hdr[3].width = Inches(1.0)
    f_hdr[4].width = Inches(0.9)
    f_hdr[5].width = Inches(0.9)
    f_hdr[6].width = Inches(1.0)

    f_titles = ["Flow ID", "Sensitive Asset", "Source -> Destination", "Process & Store", "Flow Type", "Trust Boundary", "Leakage Risk & Control"]
    for i, title in enumerate(f_titles):
        set_cell_background(f_hdr[i], "1B365D")
        set_cell_margins(f_hdr[i], top=100, bottom=100, left=60, right=60)
        p = f_hdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    flows_data = [
        ("IF-01", "A-01: Ephemeral Private Keys", "Key Negotiator (Client)\n-> Key Negotiator (Server)", "Process P2 (HKDF)\nStore DS2 (Key Cache)", "Trusted Internal\n(Parameters on Wire)", "Crosses TB2 -> TB3\n(Host OS to WAN)", "Risk: Passive recording for quantum attack.\nControl: ML-KEM-768 lattice encryption; private keys never leave local RAM."),
        ("IF-02", "A-03: Cleartext Application Data", "User Browser (Chrome/Edge)\n-> Local Proxy (127.0.0.1)", "Process P1 (SOCKS5/HTTP)\nStore DS1 (Stream Map)", "Trusted Loopback\n(Unencrypted)", "Crosses TB1\n(App to Loopback)", "Risk: Local loopback packet sniffing.\nControl: SO_EXCLUSIVEADDRUSE socket option; strictly bound to 127.0.0.1."),
        ("IF-03", "A-02, A-03: Encrypted Tunnel Frames", "AEAD Engine (Client)\n-> Cloud Demuxer (Codespaces)", "Process P3 & P5\nStore Transient Queue", "Encrypted Channel\nover Untrusted WAN", "Crosses TB3\n(Transit Public WAN)", "Risk: Man-in-the-Middle bit flipping.\nControl: AES-256-GCM AEAD (128-bit MAC) wrapped inside TLS 1.3 on Port 443."),
        ("IF-04", "A-04: DNS Query & Hostnames", "Browser SOCKS5 Client\n-> Cloud Remote DNS Resolver", "Process P1 -> P3 -> P5\nStore None", "Encrypted Tunnel\nSub-Flow", "Crosses TB3 & TB4\n(WAN to Cloud Exit)", "Risk: DNS leakage via local router UDP 53.\nControl: Strict SOCKS5 0x03 domain forwarding; resolved remotely on exit node."),
        ("IF-05", "A-03: Cleartext Egress Target Stream", "TCP Dispatcher (Codespaces)\n-> Target Internet Server", "Process P6 (Egress Relay)\nStore Kernel Buffer", "Public Egress\n(Direct Internet)", "Crosses TB4\n(Cloud to Internet)", "Risk: SSRF targeting internal cloud metadata.\nControl: Egress blacklist disallowing 169.254.0.0/16, 127.0.0.0/8, and private IPs."),
        ("IF-06", "A-06: Windows Registry Settings", "GUI Proxy Controller\n-> Windows Network Subsystem", "Process P1 / winreg\nStore DS4 (Registry)", "Trusted Host OS\nConfiguration Flow", "Crosses TB2\n(Host OS Boundary)", "Risk: Stale proxy keys breaking internet on crash.\nControl: atexit signal handlers and GUI cleanup routine reverting winreg keys.")
    ]

    for row_idx, (fid, fasset, fsd, fps, ftype, ftb, frc) in enumerate(flows_data):
        row = flow_table.add_row()
        cells = row.cells
        cells[0].width = Inches(0.6)
        cells[1].width = Inches(1.0)
        cells[2].width = Inches(1.1)
        cells[3].width = Inches(1.0)
        cells[4].width = Inches(0.9)
        cells[5].width = Inches(0.9)
        cells[6].width = Inches(1.0)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([fid, fasset, fsd, fps, ftype, ftb, frc]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=60, right=60)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.0)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 1: r.font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 4: EXERCISE 9 - VULNERABILITY ANALYSIS
    # ==========================================
    doc.add_heading("4. Phase 5 – Exercise 9: Vulnerability Analysis", level=1)
    p_ex9 = doc.add_paragraph(
        "Based on the DFD, STRIDE threat model, and Information Flow analysis, eight (8) concrete vulnerabilities "
        "have been identified. Each vulnerability details the affected DFD element, formal CWE classification, related "
        "STRIDE category, severity rating, potential impact, and the verified mitigation implemented in the Python codebase."
    )
    p_ex9.paragraph_format.space_after = Pt(8)

    vuln_table = doc.add_table(rows=1, cols=6)
    vuln_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    v_hdr = vuln_table.rows[0].cells
    v_hdr[0].width = Inches(0.6)
    v_hdr[1].width = Inches(1.3)
    v_hdr[2].width = Inches(1.0)
    v_hdr[3].width = Inches(0.8)
    v_hdr[4].width = Inches(1.3)
    v_hdr[5].width = Inches(1.5)

    v_titles = ["ID", "Vulnerability & CWE", "DFD Element & Threat", "Severity", "Impact Analysis", "Implemented Mitigation & Code"]
    for i, title in enumerate(v_titles):
        set_cell_background(v_hdr[i], "1B365D")
        set_cell_margins(v_hdr[i], top=100, bottom=100, left=70, right=70)
        p = v_hdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    vulns_data = [
        ("V-01", "Inadequate Key Size / Shor Vulnerability\n(CWE-326)", "Process P2 (Handshake)\nData Flow DF2\nThreat: T-06 (Info Leak)", "CRITICAL", "16-bit classical DH modulus (p=65521) cracked in 0.13ms by Shor's QFT algorithm, exposing AES-256 session key and historical traffic.", "NIST FIPS 203 ML-KEM-768 lattice KEM implementation; Module-LWE math provides post-quantum security margin (test_pipeline.py verified)."),
        ("V-02", "Local Loopback Port Hijacking\n(CWE-605)", "Process P1 (Local Proxy)\nData Flow DF1\nThreat: T-02 (Spoofing)", "HIGH", "On Windows, unprivileged local malware binds to 127.0.0.1:1080 without exclusive flags, stealing unencrypted browser traffic.", "Enforced SO_EXCLUSIVEADDRUSE socket option on Windows socket bind; client validates port state prior to launching proxy thread."),
        ("V-03", "DNS Query Leakage to Local Gateway\n(CWE-200)", "Process P1 & P5\nData Flow DF1\nThreat: T-07 (Info Leak)", "HIGH", "Client browser sends DNS lookups over UDP 53 to local home router instead of through tunnel, exposing visited domain names to ISP.", "Strict RFC 1928 SOCKS5 0x03 domain-name routing; domain strings are encapsulated inside tunnel and resolved remotely at cloud exit node."),
        ("V-04", "Ciphertext Bit-Flipping / Tampering\n(CWE-353)", "Process P3 (AEAD Engine)\nData Flow DF3\nThreat: T-03 (Tampering)", "HIGH", "In-transit attacker alters payload bits. If unauthenticated cipher mode (CBC/CTR) was used, altered packets execute in browser.", "AES-256-GCM AEAD mode with 128-bit authentication tag; tampered frames fail tag validation and drop connection immediately (_decrypt_frame)."),
        ("V-05", "Server-Side Request Forgery via Egress\n(CWE-918)", "Process P6 (Dispatcher)\nData Flow DF5\nThreat: T-11 (Elevation)", "HIGH", "Malicious client sends proxy requests to internal cloud metadata IP (169.254.169.254) or loopback, pivoting into host infrastructure.", "Egress IP filter in cloud_server.py blacklists link-local (169.254.0.0/16), loopback (127.0.0.0/8), and RFC 1918 private subnets."),
        ("V-06", "Asynchronous WebSocket Flooding\n(CWE-400)", "Process P5 (Cloud Gateway)\nData Flow DF3\nThreat: T-09 (DoS)", "MEDIUM", "Adversary opens hundreds of half-open WebSocket handshakes, starving server file descriptors and worker thread pool.", "Asynchronous event loop with 10.0s handshake timeout, maximum active client connection limits, and per-IP handshake rate limiting."),
        ("V-07", "Key Material Remanence in RAM\n(CWE-226)", "Data Store DS2 (Key Cache)\nThreat: T-08 (Info Leak)", "MEDIUM", "Derived AES session keys remain in Python bytearray memory space after session disconnect, susceptible to memory scraping.", "Cryptographic memory zeroization routine overwrites key buffers with zeroed bytes and calls gc.collect() upon tunnel termination."),
        ("V-08", "Orphaned System Proxy State\n(CWE-459)", "Data Store DS4 (Registry)\nThreat: T-04 (Tampering)", "MEDIUM", "Abrupt process termination (SIGKILL) leaves ProxyEnable=1 in Windows registry, disabling all internet browsing on host machine.", "Registered atexit handlers, SIGINT/SIGTERM exception wrappers, and automatic registry health-check on GUI startup restoring direct connection.")
    ]

    for row_idx, (vid, vname, vdelem, vsev, vimpact, vmit) in enumerate(vulns_data):
        row = vuln_table.add_row()
        cells = row.cells
        cells[0].width = Inches(0.6)
        cells[1].width = Inches(1.3)
        cells[2].width = Inches(1.0)
        cells[3].width = Inches(0.8)
        cells[4].width = Inches(1.3)
        cells[5].width = Inches(1.5)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([vid, vname, vdelem, vsev, vimpact, vmit]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=60, right=60)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.0)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 1: r.font.bold = True
            elif i == 3 and "CRITICAL" in val: r.font.bold = True; r.font.color.rgb = RED_ACCENT
            elif i == 3 and "HIGH" in val: r.font.bold = True; r.font.color.rgb = AMBER_ACCENT

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 5: EXERCISE 10 - ATTACK TREE ANALYSIS (PHASE 6)
    # ==========================================
    doc.add_heading("5. Phase 6 – Exercise 10: Complete Attack Tree Analysis", level=1)
    p_ex10 = doc.add_paragraph(
        "Exercise 10 models the hierarchical decomposition of attacker objectives using Bruce Schneier's Attack Tree "
        "methodology with formal AND/OR boolean logic gates."
    )
    p_ex10.paragraph_format.space_after = Pt(8)

    g_callout = doc.add_table(rows=1, cols=1)
    g_callout.alignment = WD_TABLE_ALIGNMENT.CENTER
    g_cell = g_callout.rows[0].cells[0]
    g_cell.width = Inches(6.5)
    set_cell_background(g_cell, "FBF4F4")
    set_cell_margins(g_cell, top=120, bottom=120, left=180, right=180)
    gp = g_cell.paragraphs[0]
    gp.paragraph_format.space_after = Pt(3)
    gr1 = gp.add_run("CRITICAL ATTACKER ROOT GOAL (ROOT NODE G0):\n")
    gr1.font.bold = True
    gr1.font.size = Pt(10)
    gr1.font.color.rgb = RED_ACCENT
    gr2 = gp.add_run(
        "\"Intercept and Decrypt Another User's Confidential Web Files, Active Sessions, and Credentials "
        "via Cryptographic Tunnel Compromise (Harvest Now, Decrypt Later)\"\n"
        "Alignment: Directly addresses Coursework Objective 'Accessing another user's files and confidential web data' "
        "through the exploitation of cryptographic, local host, and transport vulnerabilities."
    )
    gr2.font.size = Pt(9.5)
    gr2.font.color.rgb = CHARCOAL

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    at_table = doc.add_table(rows=1, cols=6)
    at_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    at_hdr = at_table.rows[0].cells
    at_hdr[0].width = Inches(0.7)
    at_hdr[1].width = Inches(1.2)
    at_hdr[2].width = Inches(1.8)
    at_hdr[3].width = Inches(0.9)
    at_hdr[4].width = Inches(0.8)
    at_hdr[5].width = Inches(1.1)

    at_titles = ["Path ID", "Sub-Goal / Vector", "Sequential Attack Steps (AND Gate)", "Skill / Cost", "Probability", "Engineering Mitigation"]
    for i, title in enumerate(at_titles):
        set_cell_background(at_hdr[i], "1B365D")
        set_cell_margins(at_hdr[i], top=100, bottom=100, left=70, right=70)
        p = at_hdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    attack_paths = [
        ("Path 1", "SG-1: Cryptanalytic\n(Shor's Attack on DH-16)", "1. Sniff WAN handshake packets (p, g, A, B).\nAND 2. Confirm client uses 16-bit DH mode.\nAND 3. Execute Shor 2D QFT period-finding.\nAND 4. Solve private key a in 0.13 ms.\nAND 5. Derive AES key & live-decrypt user files.", "Skill: High\nCost: Low (Commodity PC)", "CRITICAL\n(100% in DH-16)", "NIST FIPS 203 ML-KEM-768: Lattice Module-LWE math eliminates period-finding vulnerability."),
        ("Path 2", "SG-1: Cryptanalytic\n(HNDL on DH-2048)", "1. Record bulk encrypted sessions over public WAN.\nAND 2. Archive ciphertexts for future decryption.\nAND 3. Wait for Cryptanalytically Relevant Quantum Computer (CRQC >= 4096 logical qubits).\nAND 4. Retroactively compute DH-2048 private key.", "Skill: State-Actor\nCost: Extreme ($1B+)", "LOW Today\n(High in 2030+)", "Post-Quantum Migration: Deploying ML-KEM-768 today guarantees forward secrecy against future quantum computers."),
        ("Path 3", "SG-2: Host Subversion\n(Local Port Hijack)", "1. Plant unprivileged malware on host PC.\nAND 2. Race condition to bind 127.0.0.1:1080 before VPN.\nAND 3. Capture cleartext browser requests & files.", "Skill: Medium\nCost: Low", "HIGH\n(Without fix)", "SO_EXCLUSIVEADDRUSE socket option bound on Windows; validates socket ownership before proxy initialization."),
        ("Path 4", "SG-2: Host Subversion\n(Memory Scraping)", "1. Acquire local process inspection privilege.\nAND 2. Scan Python heap memory space.\nAND 3. Locate residual 256-bit AES session keys.\nAND 4. Decrypt captured tunnel packets offline.", "Skill: High\nCost: Low", "MEDIUM", "Cryptographic memory zeroization: keys overwritten with random bytes and garbage collected immediately upon tunnel close."),
        ("Path 5", "SG-2: Host Subversion\n(Registry Tampering)", "1. Inject registry edit into HKCU Internet Settings.\nAND 2. Point ProxyServer to rogue proxy IP.\nAND 3. Expose cleartext HTTP/file traffic to LAN.", "Skill: Low\nCost: Zero", "MEDIUM", "Continuous registry health verification in GUI loop; atomic restoration to direct connection on exit via wininet.dll."),
        ("Path 6", "SG-3: Cloud Gateway\n(MITM Impersonation)", "1. Poison local Wi-Fi DNS / ARP cache.\nAND 2. Intercept Port 443 HTTPS handshake.\nAND 3. Exploit disabled certificate validation.\nAND 4. Proxy victim traffic while harvesting files.", "Skill: High\nCost: Medium", "LOW\n(Mitigated)", "Strict TLS 1.3 certificate validation; ML-KEM-768 shared-secret encapsulation integrity."),
        ("Path 7", "SG-3: Cloud Gateway\n(SSRF Cloud Pivot)", "1. Connect authenticated client to cloud gateway.\nAND 2. Send SOCKS5 CONNECT to 169.254.169.254.\nAND 3. Steal cloud host infrastructure tokens.\nAND 4. Tap TCP dispatch socket P6 to sniff files.", "Skill: High\nCost: Low", "HIGH\n(Without filter)", "Cloud egress blacklist in cloud_server.py: strictly drops link-local, loopback, and private IP destination sockets."),
        ("Path 8", "SG-4: Protocol Leak\n(DNS Query Sniffing)", "1. Infiltrate victim local Wi-Fi network.\nAND 2. Filter UDP 53 DNS broadcast queries.\nAND 3. Observe cleartext domain lookups.\nAND 4. Correlate accessed files & services.", "Skill: Low\nCost: Low (Wireshark)", "MEDIUM", "Remote DNS Resolution: SOCKS5 address type 0x03 domain strings are encapsulated inside tunnel and resolved only on cloud node.")
    ]

    for row_idx, (pid, pvec, psteps, psc, pprob, pmit) in enumerate(attack_paths):
        row = at_table.add_row()
        cells = row.cells
        cells[0].width = Inches(0.7)
        cells[1].width = Inches(1.2)
        cells[2].width = Inches(1.8)
        cells[3].width = Inches(0.9)
        cells[4].width = Inches(0.8)
        cells[5].width = Inches(1.1)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([pid, pvec, psteps, psc, pprob, pmit]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=60, right=60)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.0)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 1: r.font.bold = True
            elif i == 4 and "CRITICAL" in val: r.font.bold = True; r.font.color.rgb = RED_ACCENT
            elif i == 4 and "HIGH" in val: r.font.bold = True; r.font.color.rgb = AMBER_ACCENT

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 6: PHASE 7 - UI DESIGN (EXERCISE 11)
    # ==========================================
    doc.add_heading("6. Phase 7 – UI Design: Exercise 11 (User Interface Design)", level=1)
    p_ex11 = doc.add_paragraph(
        "Exercise 11 requires designing three major screens based on requirements and use cases, specifying user types, "
        "goals, navigation, input fields, and error handling while strictly implementing the Golden Rules of UI Design "
        "(Consistency, User Control, Feedback, Error Prevention, Easy Navigation, and Clear Visibility)."
    )
    p_ex11.paragraph_format.space_after = Pt(8)

    # Golden Rules Callout
    gr_callout = doc.add_table(rows=1, cols=1)
    gr_callout.alignment = WD_TABLE_ALIGNMENT.CENTER
    gr_cell = gr_callout.rows[0].cells[0]
    gr_cell.width = Inches(6.5)
    set_cell_background(gr_cell, "F0F8F4")
    set_cell_margins(gr_cell, top=120, bottom=120, left=160, right=160)
    grp = gr_cell.paragraphs[0]
    grp.paragraph_format.space_after = Pt(2)
    gr_title = grp.add_run("THE 6 GOLDEN RULES OF UI DESIGN AS IMPLEMENTED IN SYSTEM:\n")
    gr_title.font.bold = True
    gr_title.font.size = Pt(9.5)
    gr_title.font.color.rgb = GREEN_ACCENT
    gr_body = (
        "1. Consistency: Uniform dark/cyberpunk aesthetic, standard button states, consistent cryptographic terminology.\n"
        "2. User Control: Explicit 1-click connect/disconnect, cancelable attack simulation, instant proxy rollback.\n"
        "3. Real-Time Feedback: Pulsing quantum ring status badges ('CONNECTING...', 'ML-KEM ACTIVE', 'SHOR CRACKING').\n"
        "4. Error Prevention: Disabled attack buttons during active connections; modulus sanity guards; port clash detection.\n"
        "5. Easy Navigation: Zero-install single-page tabs, sticky controls, 1-tap mobile profile installer.\n"
        "6. Clear Visibility: High contrast status indicators (Green=Secure, Red=Vulnerable, Amber=Handshaking)."
    )
    grp_run = grp.add_run(gr_body)
    grp_run.font.size = Pt(9.0)
    grp_run.font.color.rgb = CHARCOAL

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Screen 1
    doc.add_heading("6.1 Screen 1: Desktop Quantum-Safe Hybrid VPN Dashboard (quantum_vpn_gui.py)", level=2)
    p_s1 = doc.add_paragraph(
        "• User Type: End User / Student / Security Analyst.\n"
        "• User Goal: Secure local PC traffic over Port 443 with chosen cryptographic level and 1-click Windows proxying.\n"
        "• Navigation: Desktop application window with top status bar, central control card, and bottom telemetry console.\n"
        "• Required Information: Server endpoint URL, current connection state, active cipher suite, bytes TX/RX, ping latency.\n"
        "• Input Fields: Server address textbox, 3-way radio toggle (16-bit DH / 2048-bit DH / NIST ML-KEM-768), Windows Proxy toggle checkbox.\n"
        "• Error Handling: Port 1080 collision detection dialog, auto-retry on network drop, safe registry proxy rollback on crash."
    )
    p_s1.paragraph_format.space_after = Pt(6)

    # Screen 2
    doc.add_heading("6.2 Screen 2: Interactive Shor's Quantum Cryptanalysis Console", level=2)
    p_s2 = doc.add_paragraph(
        "• User Type: Academic Evaluator / Cryptographic Researcher / Student.\n"
        "• User Goal: Empirically demonstrate Shor's discrete-log quantum attack cracking 16-bit DH and live-decrypting payload.\n"
        "• Navigation: Dedicated 'Quantum Attack Simulator' tab in desktop GUI and `/api/attack` mobile dashboard.\n"
        "• Required Information: Intercepted modulus p, generator g, public keys A & B, period-finding iterations, crack time in ms, live decrypted text.\n"
        "• Input Fields: 'EXECUTE SHOR 2D QFT ATTACK' primary action button, target session selector dropdown.\n"
        "• Error Handling: Safe execution bounds (restricted to p <= 65535 to prevent GIL freeze), background daemon thread execution, 'Immune to Quantum Period Finding' banner if ML-KEM is selected."
    )
    p_s2.paragraph_format.space_after = Pt(6)

    # Screen 3
    doc.add_heading("6.3 Screen 3: Mobile Cyberpunk Web PWA & Zero-Install Gateway (cloud_server.py)", level=2)
    p_s3 = doc.add_paragraph(
        "• User Type: Smartphone User (Android / iOS) connected to restrictive home/campus Wi-Fi.\n"
        "• User Goal: Connect to cloud exit gateway in 1 tap to stream blocked sites (Netflix) without installing native APKs.\n"
        "• Navigation: Mobile-responsive viewport with bottom floating navigation pills (Tunnel Status, Attack Demo, iOS Profile, PAC Config).\n"
        "• Required Information: Cloud gateway latency, encrypted tunnel health, live Shor attack benchmark, 1-tap proxy PAC URL.\n"
        "• Input Fields: Large central holographic power toggle button ('INITIALIZE QUANTUM TUNNEL'), 'Download iOS Profile' button, 'Simulate Shor Attack' button.\n"
        "• Error Handling: Automatic WebSocket reconnect on mobile screen wake, offline status banner, mobileconfig MIME-type headers (application/x-apple-aspen-config)."
    )
    p_s3.paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 7: PHASE 8 - PRODUCT BACKLOG (EXERCISE 12)
    # ==========================================
    doc.add_heading("7. Phase 8 – Product Backlog: Exercise 12 (Agile User Stories)", level=1)
    p_ex12 = doc.add_paragraph(
        "Exercise 12 establishes the formal Agile Product Backlog derived directly from Phase 1 functional requirements "
        "and Phase 2 use cases. Ten (10) comprehensive user stories are formulated using standard Agile structure: "
        "'As a <user>, I want to <function> so that <benefit>', categorized across Epics with MoSCoW prioritization."
    )
    p_ex12.paragraph_format.space_after = Pt(8)

    # Product Backlog Table
    pb_table = doc.add_table(rows=1, cols=6)
    pb_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    pb_hdr = pb_table.rows[0].cells
    pb_hdr[0].width = Inches(0.7)  # ID
    pb_hdr[1].width = Inches(1.1)  # Epic
    pb_hdr[2].width = Inches(2.2)  # User Story
    pb_hdr[3].width = Inches(0.7)  # Priority
    pb_hdr[4].width = Inches(0.8)  # Effort
    pb_hdr[5].width = Inches(1.0)  # Traceability

    pb_titles = ["Story ID", "Epic", "User Story (Role, Feature, Benefit)", "Priority", "Effort", "Traceability"]
    for i, title in enumerate(pb_titles):
        set_cell_background(pb_hdr[i], "1B365D")
        set_cell_margins(pb_hdr[i], top=100, bottom=100, left=70, right=70)
        p = pb_hdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    stories = [
        ("US-01", "Epic 1: Quantum Cryptography", "As a Security Analyst, I want to select NIST FIPS 203 ML-KEM-768 key encapsulation so that my session traffic is immune to Harvest-Now-Decrypt-Later quantum attacks.", "MUST HAVE", "8 pts", "FR-01, UC-2\n(FIPS 203)"),
        ("US-02", "Epic 1: Quantum Cryptography", "As a Student / Researcher, I want to switch to 16-bit Diffie-Hellman mode so that I can demonstrate the mathematical mechanics of Shor's quantum algorithm.", "MUST HAVE", "5 pts", "FR-02, UC-1\n(DH-16 Mode)"),
        ("US-03", "Epic 1: Quantum Cryptography", "As an Academic Evaluator, I want to execute Shor's 2D QFT attack in real time so that I can see the private key recovered in < 1 ms and live traffic decrypted.", "MUST HAVE", "8 pts", "FR-03, UC-3\n(Shor Attack)"),
        ("US-04", "Epic 2: Network Tunneling", "As a User, I want a dual-protocol local proxy (SOCKS5 + HTTP CONNECT) on 127.0.0.1:1080 so that all browsers and apps can tunnel without external VPN drivers.", "MUST HAVE", "8 pts", "FR-04, UC-4\n(RFC 1928)"),
        ("US-05", "Epic 2: Network Tunneling", "As a User, I want the VPN to encapsulate multiplexed streams inside Port 443 TLS/WebSocket so that my traffic passes through restrictive campus/home firewalls.", "MUST HAVE", "5 pts", "FR-05, UC-2\n(Port 443 TLS)"),
        ("US-06", "Epic 2: Network Tunneling", "As a Privacy-Conscious User, I want domain names resolved remotely at the cloud exit node so that my ISP cannot observe my visited websites via DNS leaks.", "MUST HAVE", "5 pts", "FR-06, UC-4\n(Remote DNS)"),
        ("US-07", "Epic 3: User Interface", "As a Windows User, I want a 1-click system proxy toggle in the desktop GUI so that my entire OS routes through the quantum tunnel without manual proxy configuration.", "SHOULD HAVE", "5 pts", "FR-07, UC-5\n(winreg proxy)"),
        ("US-08", "Epic 3: User Interface", "As a Smartphone User, I want an eye-catching mobile PWA with 1-tap proxy profile download so that I can bypass Wi-Fi blocks on Android and iOS.", "SHOULD HAVE", "8 pts", "FR-08, UC-4\n(Mobile PWA)"),
        ("US-09", "Epic 4: Security & Assurance", "As a Systems Engineer, I want AES-256-GCM AEAD encryption on all tunnel frames so that any transit tampering or bit-flipping immediately terminates the stream.", "MUST HAVE", "5 pts", "SEC-03, UC-2\n(AEAD GCM)"),
        ("US-10", "Epic 4: Security & Assurance", "As a System Administrator, I want the cloud server to blacklist internal IP ranges (169.254.0.0/16) so that clients cannot execute SSRF attacks on cloud metadata.", "SHOULD HAVE", "3 pts", "SEC-05, UC-4\n(SSRF Filter)")
    ]

    for row_idx, (sid, sepic, sstory, sprio, seff, strace) in enumerate(stories):
        row = pb_table.add_row()
        cells = row.cells
        cells[0].width = Inches(0.7)
        cells[1].width = Inches(1.1)
        cells[2].width = Inches(2.2)
        cells[3].width = Inches(0.7)
        cells[4].width = Inches(0.8)
        cells[5].width = Inches(1.0)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([sid, sepic, sstory, sprio, seff, strace]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=60, right=60)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.0)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 1: r.font.bold = True
            elif i == 3 and "MUST" in val: r.font.bold = True; r.font.color.rgb = RED_ACCENT
            elif i == 3 and "SHOULD" in val: r.font.bold = True; r.font.color.rgb = STEEL

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 8: MATHEMATICAL & SYSTEMIC COMPARISON
    # ==========================================
    doc.add_heading("8. Cryptographic Evaluation: Classical DH vs. NIST FIPS 203 ML-KEM-768", level=1)
    p_comp = doc.add_paragraph(
        "A central requirement of the SSE evaluation is demonstrating why post-quantum cryptography is mathematically "
        "imperative to address the Information Disclosure threat (Harvest Now, Decrypt Later):"
    )
    p_comp.paragraph_format.space_after = Pt(8)

    comp_table = doc.add_table(rows=1, cols=3)
    comp_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_hdr2 = comp_table.rows[0].cells
    c_hdr2[0].width = Inches(2.0)
    c_hdr2[1].width = Inches(2.2)
    c_hdr2[2].width = Inches(2.3)

    c_titles = ["Evaluation Metric", "Classical Diffie-Hellman (16-bit / 2048-bit)", "NIST FIPS 203 (ML-KEM-768 / Kyber)"]
    for i, title in enumerate(c_titles):
        set_cell_background(c_hdr2[i], "1B365D")
        set_cell_margins(c_hdr2[i], top=100, bottom=100, left=80, right=80)
        p = c_hdr2[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(255, 255, 255)

    comp_rows = [
        ("Mathematical Foundation", "Discrete Logarithm Problem (DLP) over finite fields: g^a = A (mod p)", "Module Learning With Errors (M-LWE) over polynomial rings R_q"),
        ("Quantum Cryptanalysis", "Vulnerable to Shor's 2D QFT period-finding in polynomial time O(log^3 N)", "Immune: No known quantum polynomial algorithm for Shortest Vector Problem (SVP)"),
        ("Practical Break Time (16-bit)", "0.13 milliseconds (Demonstrated live in GUI attack console)", "Computationally infeasible (Post-Quantum Security Margin: Category 3 / 128-bit)"),
        ("Public Key / Ciphertext Size", "32 bytes (256-bit) to 256 bytes (2048-bit)", "Public Key: 1,184 bytes | Ciphertext: 1,088 bytes"),
        ("Forward Secrecy Durability", "Vulnerable to retro-active decryption by future quantum adversaries", "Guaranteed quantum-safe forward secrecy across multiple decades")
    ]

    for row_idx, (metric, classical, pqc) in enumerate(comp_rows):
        row = comp_table.add_row()
        cells = row.cells
        cells[0].width = Inches(2.0)
        cells[1].width = Inches(2.2)
        cells[2].width = Inches(2.3)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([metric, classical, pqc]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=70, bottom=70, left=80, right=80)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 1 and "0.13" in val: r.font.color.rgb = RED_ACCENT; r.font.bold = True
            elif i == 2 and "Immune" in val: r.font.color.rgb = GREEN_ACCENT; r.font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ==========================================
    # SECTION 9: VERIFICATION & CODE MAPPING
    # ==========================================
    doc.add_heading("9. Implementation Verification & Test Traceability", level=1)
    p_ver = doc.add_paragraph(
        "All mitigations specified across Phases 5, 6, 7, and 8 are backed by concrete implementations and automated tests "
        "in the project repository:"
    )
    p_ver.paragraph_format.space_after = Pt(8)

    ver_table = doc.add_table(rows=1, cols=3)
    ver_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    v_hdr2 = ver_table.rows[0].cells
    v_hdr2[0].width = Inches(2.3)
    v_hdr2[1].width = Inches(2.7)
    v_hdr2[2].width = Inches(1.5)

    v_cols = ["Security Objective", "Source Code & Test Benchmark", "Validation Status"]
    for i, title in enumerate(v_cols):
        set_cell_background(v_hdr2[i], "1B365D")
        set_cell_margins(v_hdr2[i], top=90, bottom=90, left=80, right=80)
        p = v_hdr2[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(255, 255, 255)

    ver_rows = [
        ("NIST ML-KEM-768 Lattice Handshake", "test_pipeline.py -> test_ml_kem_quantum_immunity()", "VERIFIED (Passed)"),
        ("Shor's Discrete Logarithm Engine", "quantum_vpn_gui.py -> execute_shor_attack() (0.13 ms crack)", "VERIFIED (Passed)"),
        ("AES-256-GCM AEAD Tag Integrity", "vpn_client.py -> _decrypt_frame() tag mismatch drop", "VERIFIED (Passed)"),
        ("Remote DNS Leak Prevention", "cloud_server.py -> socks5_remote_dns_resolve()", "VERIFIED (Passed)"),
        ("SO_EXCLUSIVEADDRUSE Port Binding", "vpn_client.py -> socket.SO_EXCLUSIVEADDRUSE bind", "VERIFIED (Passed)"),
        ("Egress SSRF Destination Blacklist", "cloud_server.py -> _is_forbidden_destination_ip()", "VERIFIED (Passed)"),
        ("Windows System Proxy Safe Teardown", "vpn_client.py -> unset_windows_system_proxy()", "VERIFIED (Passed)")
    ]

    for row_idx, (sobj, sref, sstat) in enumerate(ver_rows):
        row = ver_table.add_row()
        cells = row.cells
        cells[0].width = Inches(2.3)
        cells[1].width = Inches(2.7)
        cells[2].width = Inches(1.5)
        bg_color = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([sobj, sref, sstat]):
            set_cell_background(cells[i], bg_color)
            set_cell_margins(cells[i], top=60, bottom=60, left=80, right=80)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 2: r.font.bold = True; r.font.color.rgb = GREEN_ACCENT

    # Save to the exact target file
    output_path = r"v:\QUANTUM\Exercise_7_STRIDE_Threat_Analysis.docx"
    doc.save(output_path)
    print(f"[+] All Phase 5, 6, 7 & 8 exercises written to: {output_path}")

    # Also save a descriptive backup copy
    comp_path = r"v:\QUANTUM\SSE_Master_Engineering_Deliverables_Report.docx"
    doc.save(comp_path)
    print(f"[+] Master comprehensive backup saved to: {comp_path}")

if __name__ == "__main__":
    build_complete_academic_document()
