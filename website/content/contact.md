---
title: "Contact"
url: "/contact.html"
extra_styles: |
  .founder-card a > div:hover {
      transform: translateY(-4px);
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  }
  @media (max-width: 768px) {
      .founder-card a > div {
          flex-direction: column;
          text-align: center;
      }
  }
---

    <section class="hero" style="padding: 3rem 0;">
        <div class="container">
            <h2>Contact Us</h2>
            <p style="max-width: 800px; margin: 0 auto;">Get in touch with The Birthmark Standard Foundation. We're building open infrastructure for photo authentication and welcome collaboration.</p>
        </div>
    </section>

    <section class="technical-section">
        <div class="container">
            <div class="problem-grid" style="max-width: 900px; margin: 0 auto;">
                <div class="problem-card">
                    <h3>📧 Email</h3>
                    <p style="margin-bottom: 1rem;">General inquiries, partnership opportunities, and coalition membership questions:</p>
                    <p style="font-size: 1.2rem;"><a href="mailto:contact@birthmarkstandard.org" style="color: var(--accent-blue); text-decoration: none; font-weight: 600;">contact@birthmarkstandard.org</a></p>
                </div>

                <div class="problem-card">
                    <h3>💻 GitHub</h3>
                    <p style="margin-bottom: 1rem;">Explore the codebase, report issues, contribute to development, or review our technical documentation:</p>
                    <p><a href="https://github.com/Birthmark-Standard/Birthmark" style="color: var(--accent-blue); text-decoration: none; font-weight: 600;">github.com/Birthmark-Standard/Birthmark →</a></p>
                </div>
            </div>
        </div>
    </section>

    <section class="technical-section" style="background: var(--light-gray);">
        <div class="container">
            <h2>Founder</h2>
            <div class="content-block" style="max-width: 600px; margin: 0 auto;">
                <div class="founder-card">
                    <a href="https://www.linkedin.com/in/samuelcryan" target="_blank" style="text-decoration: none; color: inherit;">
                        <div style="display: flex; align-items: center; gap: 2rem; padding: 2rem; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s;">
                            <img src="/SamRyanHeadshot.jpg" alt="Samuel C. Ryan" style="width: 150px; height: 150px; border-radius: 50%; object-fit: cover; border: 4px solid var(--accent-blue);">
                            <div style="flex: 1;">
                                <h3 style="margin: 0 0 0.5rem 0; color: var(--text-color);">Samuel C. Ryan</h3>
                                <p style="margin: 0 0 1rem 0; color: var(--accent-blue); font-weight: 600;">Founder & Executive Director</p>
                                <p style="margin: 0; color: var(--gray-text); line-height: 1.6;">Building open-source infrastructure for media authentication. Former photographer and technologist committed to restoring trust in digital media.</p>
                                <div style="margin-top: 1rem;">
                                    <span style="display: inline-block; padding: 0.5rem 1rem; background: var(--accent-blue); color: white; border-radius: 4px; font-size: 0.9rem;">View LinkedIn Profile →</span>
                                </div>
                            </div>
                        </div>
                    </a>
                </div>
            </div>
        </div>
    </section>

    <section class="technical-section" style="background: var(--light-blue);">
        <div class="container">
            <h2>About The Foundation</h2>
            <div class="content-block" style="max-width: 800px; margin: 0 auto;">
                <p><strong>The Birthmark Standard Foundation</strong> is a 501(c)(3) organization in formation, dedicated to creating open-source, hardware-backed photo authentication infrastructure as a public good.</p>

                <h3 style="margin-top: 2rem;">We're Interested In:</h3>
                <ul class="technical-list">
                    <li><strong>Coalition Members:</strong> Journalism organizations, fact-checking networks, press freedom advocates, and academic institutions interested in operating validator nodes</li>
                    <li><strong>Manufacturing Partners:</strong> Camera and mobile device manufacturers interested in implementing the Birthmark Standard</li>
                    <li><strong>Grant Opportunities:</strong> Foundations and organizations supporting media integrity, journalism infrastructure, and open-source development</li>
                    <li><strong>Technical Contributors:</strong> Developers, cryptographers, and blockchain engineers interested in contributing to the open-source implementation</li>
                    <li><strong>Advisory Support:</strong> Organizations interested in serving as Founding Advisors during Phase 1 development</li>
                </ul>

                <h3 style="margin-top: 2rem;">Timeline</h3>
                <p><strong>Current Phase:</strong> Phase 1 - Hardware Prototype Development</p>
            </div>
        </div>
    </section>

    <section class="technical-section">
        <div class="container">
            <h2>Frequently Asked Questions</h2>
            <div class="content-block" style="max-width: 800px; margin: 0 auto;">
                <div class="diagram-box" style="margin-bottom: 2rem;">
                    <h4>How can my organization join the Coalition?</h4>
                    <p>We're currently in Phase 1 (development). Organizations interested in future Coalition Membership can participate as Founding Advisors. Contact us at <a href="mailto:contact@birthmarkstandard.org" style="color: var(--accent-blue);">contact@birthmarkstandard.org</a> to learn more.</p>
                </div>

                <div class="diagram-box" style="margin-bottom: 2rem;">
                    <h4>How can I contribute to the code?</h4>
                    <p>All code is open source under Apache License 2.0. Visit our <a href="https://github.com/Birthmark-Standard/Birthmark" style="color: var(--accent-blue);">GitHub repository</a> to explore the codebase, review issues, and submit pull requests.</p>
                </div>

                <div class="diagram-box" style="margin-bottom: 2rem;">
                    <h4>Can I use Birthmark Standard in my camera product?</h4>
                    <p>Yes! We're actively seeking manufacturing partnerships. The system is designed to integrate with existing camera hardware. Contact us to discuss technical requirements and implementation timelines.</p>
                </div>

                <div class="diagram-box">
                    <h4>Is there a demo or proof-of-concept available?</h4>
                    <p>We're currently building the Phase 1 hardware prototype using Raspberry Pi 4 + HQ Camera. Technical specifications and progress updates are available on <a href="https://github.com/Birthmark-Standard/Birthmark" style="color: var(--accent-blue);">GitHub</a>.</p>
                </div>
            </div>
        </div>
    </section>
