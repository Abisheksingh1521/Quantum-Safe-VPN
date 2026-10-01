import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
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

def create_cicd_document():
    doc = Document()

    # Color Palette matching SpyAware style + Quantum theme
    NAVY = RGBColor(27, 54, 93)       # #1B365D
    STEEL = RGBColor(75, 107, 148)    # #4B6B94
    CHARCOAL = RGBColor(40, 40, 40)   # #282828
    GREEN_ACCENT = RGBColor(30, 130, 60)
    CODE_BG = "F4F6F9"

    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = CHARCOAL

    # Document Header / Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_sub = p_title.add_run("SOFTWARE SYSTEMS & DEVOPS ENGINEERING • TECHNICAL REPORT\n")
    r_sub.font.size = Pt(9.5)
    r_sub.font.bold = True
    r_sub.font.color.rgb = STEEL

    r_main = p_title.add_run("Quantum-Safe Hybrid VPN Testbed\nDevOps & CI/CD Implementation")
    r_main.font.size = Pt(22)
    r_main.font.bold = True
    r_main.font.color.rgb = NAVY

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(4)
    p_meta.paragraph_format.space_after = Pt(16)
    r_meta = p_meta.add_run(
        "Project: Quantum-Safe Hybrid VPN with Shor's Attack Simulation & NIST FIPS 203 (ML-KEM-768)\n"
        "DevOps Stack: Git, GitHub, Docker 29.5, GitHub Actions, Python 3.13, PyInstaller\n"
        "Document Version: 1.0.0 | Date: October 2026 | Status: Production Verified"
    )
    r_meta.font.size = Pt(9.0)
    r_meta.font.italic = True
    r_meta.font.color.rgb = STEEL

    # 1. Project Overview
    doc.add_heading("1. Project Overview", level=1)
    p = doc.add_paragraph(
        "The Quantum-Safe Hybrid VPN Testbed is a high-performance network security application designed to "
        "demonstrate both the mathematical vulnerabilities of classical 16-bit Diffie-Hellman handshakes against "
        "Shor's quantum algorithm and the robust mathematical immunity provided by NIST FIPS 203 (ML-KEM-768 / Kyber) "
        "lattice-based post-quantum cryptography. The system incorporates a dual-mode local proxy (RFC 1928 SOCKS5 + HTTP CONNECT) "
        "on 127.0.0.1:1080, an asynchronous multiplexed WebSocket cloud exit gateway operating over Port 443 HTTPS, and "
        "cross-platform clients (Windows Desktop GUI with 1-click proxy auto-configuration and a Mobile Cyberpunk Web PWA)."
    )
    p.paragraph_format.space_after = Pt(6)

    p_devops = doc.add_paragraph(
        "As part of the project engineering lifecycle, an automated DevOps and DevSecOps workflow was implemented "
        "using Git, GitHub, Docker, and GitHub Actions to ensure code quality, reproducible containerized builds, "
        "continuous verification of cryptographic algorithms, and automated versioned artifact releases."
    )
    p_devops.paragraph_format.space_after = Pt(6)

    p_obj_head = doc.add_paragraph()
    r = p_obj_head.add_run("Key DevOps Objectives:")
    r.font.bold = True
    obj_list = [
        "Maintain version-controlled codebase using Git and GitHub with strict branching.",
        "Containerize the Python cloud exit gateway using Docker for reproducible execution.",
        "Automate cryptographic pipeline execution and Shor attack verification via CI.",
        "Implement a multi-job GitHub Actions CI/CD pipeline triggered on pushes and pull requests.",
        "Create automated versioned releases and distributable client packages on Git tags (v*)."
    ]
    for obj in obj_list:
        p_item = doc.add_paragraph(f"• {obj}")
        p_item.paragraph_format.space_after = Pt(3)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 2. Technologies Used
    doc.add_heading("2. Technologies Used", level=1)
    p_tech = doc.add_paragraph("The DevOps pipeline utilizes modern industry-standard automation and containerization tools:")
    p_tech.paragraph_format.space_after = Pt(6)

    tech_table = doc.add_table(rows=1, cols=3)
    tech_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    thdr = tech_table.rows[0].cells
    thdr[0].width = Inches(1.8)
    thdr[1].width = Inches(1.8)
    thdr[2].width = Inches(2.9)
    for i, title in enumerate(["Technology", "Version / Platform", "Purpose in DevOps Pipeline"]):
        set_cell_background(thdr[i], "1B365D")
        set_cell_margins(thdr[i], top=90, bottom=90, left=80, right=80)
        p = thdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(255, 255, 255)

    tech_data = [
        ("Git", "2.45.2 (Windows / Linux)", "Distributed version control and release tagging"),
        ("GitHub", "Cloud Enterprise", "Remote source-code hosting, issue tracking, and releases"),
        ("Docker", "29.5.2 (Engine & CLI)", "Reproducible containerized runtime for Cloud Gateway"),
        ("GitHub Actions", "v4 Runner (Ubuntu 24.04)", "Automated CI/CD workflows, testing, and release delivery"),
        ("Python", "3.13.x Runtime", "Core application programming language"),
        ("cryptography", "43.0.x Library", "Production AES-256-GCM AEAD and HKDF-SHA256 implementations"),
        ("Docker Buildx", "v3 Action", "Optimized layer caching and multi-stage container building"),
        ("Linux / Windows", "Cross-Platform", "Target deployment environments for Client and Gateway")
    ]
    for row_idx, (t_name, t_ver, t_purp) in enumerate(tech_data):
        row = tech_table.add_row()
        cells = row.cells
        cells[0].width = Inches(1.8)
        cells[1].width = Inches(1.8)
        cells[2].width = Inches(2.9)
        bg = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([t_name, t_ver, t_purp]):
            set_cell_background(cells[i], bg)
            set_cell_margins(cells[i], top=60, bottom=60, left=80, right=80)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 3. Git and GitHub Setup
    doc.add_heading("3. Git and GitHub Setup", level=1)
    p_git = doc.add_paragraph(
        "The project repository is configured with SSH authentication for secure, key-based commits. "
        "The main development branch is synchronized with GitHub origin:"
    )
    p_git.paragraph_format.space_after = Pt(4)

    git_cmds = (
        "git init\n"
        "git remote add origin git@github.com:<username>/Quantum-Safe-VPN.git\n"
        "ssh -T git@github.com\n"
        "git branch -M main\n"
        "git add .\n"
        "git commit -m \"feat: Initial commit for Quantum-Safe Hybrid VPN Testbed with CI/CD\"\n"
        "git push -u origin main"
    )
    callout_git = doc.add_table(rows=1, cols=1)
    callout_git.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = callout_git.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=120, right=120)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(git_cmds)
    r.font.name = 'Consolas'
    r.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    p_clean = doc.add_paragraph(
        "Source-Control Cleanup & .gitignore Configuration:\n"
        "To prevent machine-specific artifacts, virtual environment binaries, and sensitive temporary caches "
        "from contaminating the repository, a strict .gitignore was established containing:"
    )
    p_clean.paragraph_format.space_after = Pt(4)

    ign_text = (
        "__pycache__/\n*.py[cod]\n*$py.class\n.pytest_cache/\nbuild/\ndist/\n*.exe\n"
        ".env\n.venv/\nvenv/\n*.log\nscratch/\n.system_generated/"
    )
    callout_ign = doc.add_table(rows=1, cols=1)
    callout_ign.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = callout_ign.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=120, right=120)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(ign_text)
    r.font.name = 'Consolas'
    r.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 4. Docker Containerization
    doc.add_heading("4. Docker Containerization", level=1)
    p_dock = doc.add_paragraph(
        "The Quantum-Safe VPN Cloud Gateway Exit Node is containerized to ensure full reproducibility across cloud "
        "providers (GitHub Codespaces, AWS EC2, or Docker Desktop). The container packages the Python 3.13 slim base "
        "environment, installs cryptographic dependencies, enforces a non-root security context (USER vpnuser), and "
        "automatically executes test_pipeline.py during the container build to prevent defective images from being built."
    )
    p_dock.paragraph_format.space_after = Pt(6)

    p_d_cmd = doc.add_paragraph("The container image is built using standard Docker commands:")
    p_d_cmd.paragraph_format.space_after = Pt(4)

    d_build_cmd = "docker build -t quantum-vpn-gateway:latest ."
    c_tbl = doc.add_table(rows=1, cols=1)
    c_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = c_tbl.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=120, right=120)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(d_build_cmd)
    r.font.name = 'Consolas'
    r.font.size = Pt(9.0)
    r.font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 5. Building and Running Using Docker
    doc.add_heading("5. Building and Running Using Docker", level=1)
    p_run = doc.add_paragraph(
        "The gateway container exposes Port 8888 and handles asynchronous WebSocket and HTTP CONNECT tunnel "
        "traffic with built-in health probes:"
    )
    p_run.paragraph_format.space_after = Pt(4)

    d_run_cmd = (
        "# Run containerized VPN Cloud Gateway in background\n"
        "docker run -d --name vpn-gateway -p 8888:8888 quantum-vpn-gateway:latest\n\n"
        "# Verify container health and HTTP responsiveness\n"
        "curl -f http://localhost:8888/ || exit 1\n\n"
        "# Execute cryptographic pipeline test directly inside running container\n"
        "docker exec -it vpn-gateway python test_pipeline.py"
    )
    c_tbl2 = doc.add_table(rows=1, cols=1)
    c_tbl2.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = c_tbl2.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=120, right=120)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(d_run_cmd)
    r.font.name = 'Consolas'
    r.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 6. CI — Continuous Integration
    doc.add_heading("6. CI — Continuous Integration", level=1)
    p_ci = doc.add_paragraph(
        "Continuous Integration is automated using GitHub Actions via `.github/workflows/ci-cd.yml`. "
        "Every push or pull request to the `main` branch triggers an automated multi-stage pipeline:"
    )
    p_ci.paragraph_format.space_after = Pt(6)

    ci_flow = (
        "Git Push to main\n"
        "      │\n"
        "      ▼\n"
        "GitHub Actions Runner (Ubuntu 24.04)\n"
        "      │\n"
        "      ├── Job 1: Checkout Code & Setup Python 3.13\n"
        "      │          └── Execute 'python test_pipeline.py' (Verify ML-KEM-768 & Shor Crack)\n"
        "      │\n"
        "      ├── Job 2: Build Docker Image ('docker build -t quantum-vpn-gateway .')\n"
        "      │          └── Execute Container Runtime Smoke Test on Port 8888\n"
        "      │\n"
        "      └── Job 3: Package Client & Server Distribution Zip\n"
        "                 └── Upload Artifact: 'Quantum-Safe-VPN-Bundle' (Retention: 14 Days)"
    )
    c_tbl3 = doc.add_table(rows=1, cols=1)
    c_tbl3.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = c_tbl3.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=120, right=120)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(ci_flow)
    r.font.name = 'Consolas'
    r.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 7. CD — Continuous Delivery
    doc.add_heading("7. CD — Continuous Delivery", level=1)
    p_cd = doc.add_paragraph(
        "Continuous Delivery is triggered via Git semantic version tags (`v*`). When a tag is pushed, the CD pipeline "
        "automatically packages the distribution bundle, creates an official GitHub Release, and publishes the downloadable "
        "client and server ZIP archive:"
    )
    p_cd.paragraph_format.space_after = Pt(4)

    cd_cmds = (
        "git tag v1.0.0\n"
        "git push origin v1.0.0"
    )
    c_tbl4 = doc.add_table(rows=1, cols=1)
    c_tbl4.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = c_tbl4.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=120, right=120)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(cd_cmds)
    r.font.name = 'Consolas'
    r.font.size = Pt(9.0)
    r.font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    p_rel_info = doc.add_paragraph(
        "The automated release publishes `Quantum-Safe-VPN-Client-v1.0.0.zip` containing the Desktop Tkinter GUI, "
        "the local dual-mode SOCKS5 proxy, the batch launcher (`start_gui.bat`), and the cloud exit server."
    )
    p_rel_info.paragraph_format.space_after = Pt(10)

    # 8. Final DevOps Architecture
    doc.add_heading("8. Final DevOps Architecture", level=1)
    p_arch = doc.add_paragraph("The complete end-to-end architecture is summarized in the structural flow diagram below:")
    p_arch.paragraph_format.space_after = Pt(6)

    arch_diagram = (
        "   +-------------------------------------------------------------+\n"
        "   |                     Developer Workstation                   |\n"
        "   |  (Python 3.13, Tkinter GUI, Git 2.45, Local SOCKS5 Proxy)   |\n"
        "   +------------------------------+------------------------------+\n"
        "                                  | git push (Code or v* Tag)\n"
        "                                  v\n"
        "   +-------------------------------------------------------------+\n"
        "   |                  GitHub Cloud Repository                    |\n"
        "   |      (SSH Authenticated, .gitignore, Branch Protection)     |\n"
        "   +------------------------------+------------------------------+\n"
        "                                  | Webhook Trigger\n"
        "                                  v\n"
        "   +-------------------------------------------------------------+\n"
        "   |                  GitHub Actions CI/CD Pipeline              |\n"
        "   |  +---------------------+   +-----------------------------+  |\n"
        "   |  | Cryptographic Tests |   |    Docker Image Build       |  |\n"
        "   |  | (ML-KEM & Shor DL)  |   | (python:3.13-slim Container)|  |\n"
        "   |  +----------+----------+   +--------------+--------------+  |\n"
        "   +-------------|-----------------------------|-----------------+\n"
        "                 | Artifact Upload             | Tag Trigger\n"
        "                 v                             v\n"
        "   +-----------------------------+   +-----------------------------+\n"
        "   |   GitHub Actions Artifact   |   |    GitHub Official Release  |\n"
        "   | (Client Distribution .zip)  |   | (v1.0.0 + Downloadable Pkg) |\n"
        "   +-----------------------------+   +-----------------------------+"
    )
    c_tbl5 = doc.add_table(rows=1, cols=1)
    c_tbl5.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_cell = c_tbl5.rows[0].cells[0]
    c_cell.width = Inches(6.5)
    set_cell_background(c_cell, CODE_BG)
    set_cell_margins(c_cell, top=80, bottom=80, left=100, right=100)
    cp = c_cell.paragraphs[0]
    r = cp.add_run(arch_diagram)
    r.font.name = 'Consolas'
    r.font.size = Pt(8.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 9. Security Considerations (DevSecOps)
    doc.add_heading("9. Security Considerations (DevSecOps)", level=1)
    sec_points = [
        ("Non-Root Container User: ", "The Dockerfile explicitly creates and runs under 'USER vpnuser' (UID 1001), preventing container breakout into root host privileges."),
        ("Automated Cryptographic Verification: ", "The container build step and CI pipeline execute test_pipeline.py, guaranteeing that quantum resilience and Shor's attack simulator pass before deployment."),
        ("No Hardcoded Secrets: ", "All private keys, AES session keys, and tokens are generated ephemerally in RAM using os.urandom; zero secrets are stored in Git."),
        ("Port 443 TLS Encapsulation: ", "External cloud communication is wrapped inside standard TLS 1.3 over Port 443, mitigating traffic inspection and firewall packet drops."),
        ("Repository Hygiene: ", "All virtual environments, temporary tokens, local proxy caches, and logs are excluded from Git via .gitignore.")
    ]
    for title, desc in sec_points:
        p_s = doc.add_paragraph()
        p_s.paragraph_format.space_after = Pt(4)
        r1 = p_s.add_run(f"• {title}")
        r1.font.bold = True
        r1.font.color.rgb = NAVY
        r2 = p_s.add_run(desc)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 10. Results Checklist
    doc.add_heading("10. Results & Implementation Verification", level=1)
    p_res = doc.add_paragraph("The following DevOps components have been fully constructed and validated:")
    p_res.paragraph_format.space_after = Pt(6)

    res_table = doc.add_table(rows=1, cols=3)
    res_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    rhdr = res_table.rows[0].cells
    rhdr[0].width = Inches(2.2)
    rhdr[1].width = Inches(2.8)
    rhdr[2].width = Inches(1.5)
    for i, title in enumerate(["DevOps Task", "Implementation File / Artifact", "Verification Status"]):
        set_cell_background(rhdr[i], "1B365D")
        set_cell_margins(rhdr[i], top=90, bottom=90, left=80, right=80)
        p = rhdr[i].paragraphs[0]
        r = p.add_run(title)
        r.font.bold = True
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(255, 255, 255)

    res_data = [
        ("Git Repository Setup", ".git configuration with SSH remote", "✅ Completed"),
        ("Source Control Cleanup", ".gitignore tailored for Python & VPN", "✅ Completed"),
        ("Docker Containerization", "Dockerfile with non-root security", "✅ Completed"),
        ("Cryptographic Build Tests", "RUN python test_pipeline.py in image", "✅ Completed"),
        ("CI Pipeline Automation", ".github/workflows/ci-cd.yml", "✅ Completed"),
        ("Automated Quantum Tests", "GitHub Actions Python 3.13 Test Job", "✅ Completed"),
        ("Distribution Packaging", "Artifact zip creation & upload", "✅ Completed"),
        ("Version Tagging (v1.0.0)", "Git tag trigger for release", "✅ Completed"),
        ("CD Release Automation", "softprops/action-gh-release@v2", "✅ Implemented")
    ]
    for row_idx, (d_task, d_file, d_stat) in enumerate(res_data):
        row = res_table.add_row()
        cells = row.cells
        cells[0].width = Inches(2.2)
        cells[1].width = Inches(2.8)
        cells[2].width = Inches(1.5)
        bg = "F9FBFD" if row_idx % 2 == 0 else "FFFFFF"
        for i, val in enumerate([d_task, d_file, d_stat]):
            set_cell_background(cells[i], bg)
            set_cell_margins(cells[i], top=60, bottom=60, left=80, right=80)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if i == 0: r.font.bold = True; r.font.color.rgb = NAVY
            elif i == 2: r.font.bold = True; r.font.color.rgb = GREEN_ACCENT

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 11. Future Improvements
    doc.add_heading("11. Future Improvements", level=1)
    fut_list = [
        "Static Application Security Testing (SAST) using Bandit to continuously scan Python source code for security flaws.",
        "Container Vulnerability Scanning using Trivy or Snyk in the GitHub Actions workflow to detect vulnerable base image packages.",
        "Software Bill of Materials (SBOM) generation (SPDX / CycloneDX format) for supply chain transparency.",
        "Automated Multi-Architecture Docker Builds targeting both linux/amd64 and linux/arm64 (Apple Silicon / Raspberry Pi).",
        "Code Coverage Reporting integrated with Codecov to enforce 90%+ branch test coverage on cryptographic modules."
    ]
    for item in fut_list:
        p_f = doc.add_paragraph(f"• {item}")
        p_f.paragraph_format.space_after = Pt(3)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 12. Conclusion
    doc.add_heading("12. Conclusion", level=1)
    p_concl = doc.add_paragraph(
        "The Quantum-Safe Hybrid VPN Testbed was successfully integrated with an end-to-end DevOps and CI/CD "
        "pipeline using Git, GitHub, Docker, and GitHub Actions. Docker provides a standardized, reproducible "
        "environment for running the Python cloud exit gateway under a non-root security context. GitHub Actions "
        "automates unit testing, Shor algorithm verification, and ML-KEM-768 quantum immunity validation on every code change. "
        "Semantic version tagging (v1.0.0) triggers automated releases, delivering distributable client and server packages. "
        "This pipeline establishes a robust engineering foundation for future DevSecOps maturity, ensuring rapid, reliable, "
        "and mathematically verified software delivery."
    )
    p_concl.paragraph_format.space_after = Pt(12)

    # Save to disk
    out_path = r"v:\QUANTUM\QuantumSafe_VPN_CI_CD_Documentation.docx"
    doc.save(out_path)
    print(f"[+] CI/CD Documentation generated successfully at: {out_path}")

if __name__ == "__main__":
    create_cicd_document()
