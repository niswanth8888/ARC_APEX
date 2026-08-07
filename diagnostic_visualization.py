# ============================================================
# Diagnostic Report Visualization & Runtime Monitoring
# ============================================================

# Overview:
# This module displays the diagnostic report generated during
# ARC APEX execution. For development and offline benchmark runs,
# the generated HTML report is rendered directly within the
# notebook, providing an interactive view of execution results,
# logs, and performance insights. During competition submissions,
# diagnostics are intentionally disabled to optimize runtime.

# Purpose:
# Provides a convenient interface for reviewing execution
# diagnostics after benchmark completion. It enables developers
# to inspect generated reports without leaving the notebook while
# automatically handling cases where diagnostics are unavailable.

# Workflow:
#
#        Benchmark Completed
#                |
#                v
#    Check Diagnostic Report
#                |
#       +--------+--------+
#       |                 |
#       v                 v
#   Report Found     Report Missing
#       |                 |
#       v                 v
# Render HTML        Display Status
#    in Notebook       Message
#       |                 |
#       +--------+--------+
#                |
#                v
#     Diagnostic Review Complete
#
# ============================================================


from html import escape

from IPython.display import HTML, display


# Locate the diagnostic report generated during benchmark execution.
diagnostics_html = WORKING_DIR / "diagnostics.html"

if diagnostics_html.is_file():

    # Render the diagnostic report inside an isolated iframe to
    # prevent the report styling from affecting the notebook layout.
    display(
        HTML(
            f'<iframe srcdoc="{escape(diagnostics_html.read_text(), quote=True)}" '
            'width="100%" height="900" style="border:0"></iframe>'
        )
    )

else:

    # Notify the user when diagnostic generation has been disabled,
    # which typically occurs during official competition submissions.
    print(
        "No diagnostics.html — minimal diagnostics (real submission) suppresses it."
    )
