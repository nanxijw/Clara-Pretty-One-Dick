#Embedded file name: coverage\xmlreport.py
"""XML reporting for coverage.py"""
import os, sys, time
import xml.dom.minidom
from coverage import __url__, __version__
from coverage.backward import sorted, rpartition
from coverage.report import Reporter

def rate(hit, num):
    """Return the fraction of `hit`/`num`, as a string."""
    return '%.4g' % (float(hit) / (num or 1.0))


class XmlReporter(Reporter):
    """A reporter for writing Cobertura-style XML coverage results."""

    def __init__(self, coverage, config):
        super(XmlReporter, self).__init__(coverage, config)
        self.packages = None
        self.xml_out = None
        self.arcs = coverage.data.has_arcs()

    def report(self, morfs, outfile = None):
        """Generate a Cobertura-compatible XML report for `morfs`.
        
        `morfs` is a list of modules or filenames.
        
        `outfile` is a file object to write the XML to.
        
        """
        outfile = outfile or sys.stdout
        impl = xml.dom.minidom.getDOMImplementation()
        docType = impl.createDocumentType('coverage', None, 'http://cobertura.sourceforge.net/xml/coverage-03.dtd')
        self.xml_out = impl.createDocument(None, 'coverage', docType)
        xcoverage = self.xml_out.documentElement
        xcoverage.setAttribute('version', __version__)
        xcoverage.setAttribute('timestamp', str(int(time.time() * 1000)))
        xcoverage.appendChild(self.xml_out.createComment(' Generated by coverage.py: %s ' % __url__))
        xpackages = self.xml_out.createElement('packages')
        xcoverage.appendChild(xpackages)
        self.packages = {}
        self.report_files(self.xml_file, morfs)
        lnum_tot, lhits_tot = (0, 0)
        bnum_tot, bhits_tot = (0, 0)
        for pkg_name in sorted(self.packages.keys()):
            pkg_data = self.packages[pkg_name]
            class_elts, lhits, lnum, bhits, bnum = pkg_data
            xpackage = self.xml_out.createElement('package')
            xpackages.appendChild(xpackage)
            xclasses = self.xml_out.createElement('classes')
            xpackage.appendChild(xclasses)
            for class_name in sorted(class_elts.keys()):
                xclasses.appendChild(class_elts[class_name])

            xpackage.setAttribute('name', pkg_name.replace(os.sep, '.'))
            xpackage.setAttribute('line-rate', rate(lhits, lnum))
            xpackage.setAttribute('branch-rate', rate(bhits, bnum))
            xpackage.setAttribute('complexity', '0')
            lnum_tot += lnum
            lhits_tot += lhits
            bnum_tot += bnum
            bhits_tot += bhits

        xcoverage.setAttribute('line-rate', rate(lhits_tot, lnum_tot))
        xcoverage.setAttribute('branch-rate', rate(bhits_tot, bnum_tot))
        outfile.write(self.xml_out.toprettyxml())
        denom = lnum_tot + bnum_tot
        if denom == 0:
            pct = 0.0
        else:
            pct = 100.0 * (lhits_tot + bhits_tot) / denom
        return pct

    def xml_file(self, cu, analysis):
        """Add to the XML report for a single file."""
        package_name = rpartition(cu.name, '.')[0]
        className = cu.name
        package = self.packages.setdefault(package_name, [{},
         0,
         0,
         0,
         0])
        xclass = self.xml_out.createElement('class')
        xclass.appendChild(self.xml_out.createElement('methods'))
        xlines = self.xml_out.createElement('lines')
        xclass.appendChild(xlines)
        xclass.setAttribute('name', className)
        filename = cu.file_locator.relative_filename(cu.filename)
        xclass.setAttribute('filename', filename.replace('\\', '/'))
        xclass.setAttribute('complexity', '0')
        branch_stats = analysis.branch_stats()
        for line in analysis.statements:
            xline = self.xml_out.createElement('line')
            xline.setAttribute('number', str(line))
            xline.setAttribute('hits', str(int(line not in analysis.missing)))
            if self.arcs:
                if line in branch_stats:
                    total, taken = branch_stats[line]
                    xline.setAttribute('branch', 'true')
                    xline.setAttribute('condition-coverage', '%d%% (%d/%d)' % (100 * taken / total, taken, total))
            xlines.appendChild(xline)

        class_lines = len(analysis.statements)
        class_hits = class_lines - len(analysis.missing)
        if self.arcs:
            class_branches = sum([ t for t, k in branch_stats.values() ])
            missing_branches = sum([ t - k for t, k in branch_stats.values() ])
            class_br_hits = class_branches - missing_branches
        else:
            class_branches = 0.0
            class_br_hits = 0.0
        xclass.setAttribute('line-rate', rate(class_hits, class_lines))
        xclass.setAttribute('branch-rate', rate(class_br_hits, class_branches))
        package[0][className] = xclass
        package[1] += class_hits
        package[2] += class_lines
        package[3] += class_br_hits
        package[4] += class_branches
