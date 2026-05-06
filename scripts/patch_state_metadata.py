"""
Patch state_metadata.yaml with researched status tiers, lead agencies,
deadlines, and portal URLs.

Source: research conducted 2026-05-05 via HUD OZ portal, EIG Designation
Leads map, state agency pages, and Novogradac state tracker.

Run: python scripts/patch_state_metadata.py
Idempotent — safe to re-run.
"""

import yaml
from pathlib import Path

YAML_PATH = Path(__file__).parent.parent / "state_metadata.yaml"


def agency(name, url, email=None, phone=None):
    return {"name": name, "url": url, "contact_email": email, "contact_phone": phone}


PATCHES = {
    "alabama": {
        "status_tier": "contact_only",
        "lead_agency": agency("Alabama Department of Economic and Community Affairs (ADECA)", "https://adeca.alabama.gov/opportunityzones/"),
        "notes": "No OZ 2.0 process published as of 2026-05-05. ADECA is confirmed lead per EIG map.",
    },
    "alaska": {
        "status_tier": "contact_only",
        "lead_agency": agency("Alaska Dept. of Commerce, Community, and Economic Development", "https://www.commerce.alaska.gov/web/", "dcced.commissioner@alaska.gov", "(907) 465-2500"),
        "notes": "DCCED confirmed lead. No OZ 2.0 nomination process or deadline published.",
    },
    "arizona": {
        "status_tier": "public_process",
        "lead_agency": agency("Arizona Commerce Authority (ACA)", "https://www.azcommerce.com/arizona-opportunity-zones/oz-20-recommendation-process/", "oz@azcommerce.com"),
        "application_portal_url": "https://www.azcommerce.com/arizona-opportunity-zones/oz-20-recommendation-process/",
        "process": "ACA published a recommendation process with criteria including investment-ready sites, zoning, and infrastructure. Mapping tool in development. ACA intends to submit to Treasury on or around July 1, 2026.",
        "notes": "Deadline described as mid-May 2026 but not officially set as of 2026-05-05.",
    },
    "arkansas": {
        "status_tier": "contact_only",
        "lead_agency": agency("Arkansas Economic Development Commission (AEDC)", "https://www.arkansasedc.com/community-resources/opportunity-zones"),
        "notes": "AEDC page addresses OZ 1.0 only as of 2026-05-05. No OZ 2.0 guidance published.",
    },
    "california": {
        "status_tier": "contact_only",
        "lead_agency": agency("Governor's Office of Business and Economic Development (GO-Biz)", "https://business.ca.gov/resources/infrastructure-development/opportunity-zones-in-california/"),
        "notes": "GO-Biz acknowledges July 1, 2026 federal window and directs stakeholders to Help Center. No formal application or deadline published.",
    },
    "colorado": {
        "status_tier": "contact_only",
        "lead_agency": agency("Colorado Office of Economic Development and International Trade (OEDIT)", "https://oedit.colorado.gov/colorado-opportunity-zone-program"),
        "notes": "Multi-month stakeholder engagement underway. Public GIS mapping tool and nomination feedback in development but not yet live as of 2026-05-05.",
    },
    "connecticut": {
        "status_tier": "contact_only",
        "lead_agency": agency("Connecticut Dept. of Economic and Community Development (DECD)", "https://portal.ct.gov/DECD/Services/Business-Development/Tax-Incentives/Opportunity-Zones", "DECD.ozprojects@ct.gov", "(860) 280-8710"),
        "notes": "Contact confirmed. No application portal or deadline published.",
    },
    "delaware": {
        "status_tier": "public_process",
        "lead_agency": agency("Delaware Division of Small Business", "https://business.delaware.gov/opportunity-zones/", "business@delaware.gov", "(302) 739-4271"),
        "state_deadline": "2026-05-15",
        "application_portal_url": "https://degovforms.formstack.com/forms/opportunityzonenomination",
        "process": "Formstack nomination portal launched March 2026. Community nomination deadline May 15, 2026. Governor may nominate maximum 25 tracts.",
        "notes": "Nomination window closing or closed as of check date. No scoring rubric published.",
    },
    "district-of-columbia": {
        "status_tier": "no_public_process",
        "lead_agency": agency("DC Office of the Deputy Mayor for Planning and Economic Development (DMPED)", None),
        "notes": "DMPED presumed lead. No OZ 2.0 guidance published. DC eligible for statutory minimum 25 zones.",
    },
    "florida": {
        "status_tier": "public_process",
        "lead_agency": agency("FloridaCommerce", "https://floridajobs.org/business-growth-and-partnerships/for-businesses-and-entrepreneurs/business-resource/opportunity-zones-program"),
        "application_portal_url": "https://www.floridajobs.org/OpportunityZones",
        "state_deadline": "2026-04-30",
        "process": "FloridaCommerce ran a statewide OZ 2.0 Tour February–April 2026, soliciting community recommendations. Public input window closed approximately April 30, 2026. State is now preparing gubernatorial recommendations.",
        "notes": "Public input window closed. 340 tracts to be nominated from 1,360 eligible.",
    },
    "georgia": {
        "status_tier": "contact_only",
        "lead_agency": agency("Georgia Department of Community Affairs (DCA)", "https://dca.georgia.gov/financing-tools/incentives/federal-opportunity-zones", "federalopportunityzones@dca.ga.gov", "(404) 679-4840"),
        "notes": "DCA confirmed lead. No OZ 2.0 application or deadline published.",
    },
    "hawaii": {
        "status_tier": "contact_only",
        "lead_agency": agency("Hawaii Dept. of Business, Economic Development and Tourism (DBEDT)", "https://invest.hawaii.gov/business-programs/opportunity-zones/about-opportunity-zones/"),
        "notes": "DBEDT confirmed lead. No OZ 2.0 nomination guidance or deadline published.",
    },
    "idaho": {
        "status_tier": "public_process",
        "lead_agency": agency("Idaho Commerce", "https://commerce.idaho.gov/incentives-and-financing/opportunity-zones/", "OZ@commerce.idaho.gov"),
        "process": "Idaho Commerce published a nomination portal for cities, counties, and tribal governments. Deadline not yet published. Idaho subject to statutory minimum of 25 zones.",
        "notes": "Portal live but deadline unknown as of 2026-05-05.",
    },
    "illinois": {
        "status_tier": "public_process",
        "lead_agency": agency("Illinois Dept. of Commerce and Economic Opportunity (DCEO)", "https://dceo.illinois.gov/oppzn.html", "opportunityzones@illinois.gov"),
        "application_portal_url": "https://app.smartsheet.com/b/form/047a54ef882c425694cfb626d9050041",
        "process": "DCEO published a live Smartsheet nomination form. Webinar recording and FAQ available. No deadline published as of 2026-05-05.",
        "notes": "238 tracts to be nominated from 950 eligible.",
    },
    "indiana": {
        "status_tier": "contact_only",
        "lead_agency": agency("Indiana Economic Development Corporation (IEDC)", "https://iedc.in.gov/program/indiana-opportunity-zones/overview", None, "(317) 232-8800"),
        "notes": "IEDC page references federal September 28, 2026 deadline. No internal state application process published.",
    },
    "iowa": {
        "status_tier": "contact_only",
        "lead_agency": agency("Iowa Economic Development Authority (IEDA)", "https://opportunityiowa.gov/community/revitalization/opportunity-zones"),
        "notes": "IEDA confirmed lead. No OZ 2.0 nomination process published.",
    },
    "kansas": {
        "status_tier": "public_process",
        "lead_agency": agency("Kansas Department of Commerce", "https://www.kansascommerce.gov/opportunity-zones-2-0/", "OZ@kansascommerce.gov"),
        "state_deadline": "2026-06-01",
        "scoring_rubric_url": "https://www.kansascommerce.gov/opportunity-zones-2-0/",
        "process": "Community nominations due June 1, 2026 via email to OZ@kansascommerce.gov. Scoring matrix published. No online portal — email submission only. Workshops offered.",
        "notes": "53 tracts to be nominated.",
    },
    "kentucky": {
        "status_tier": "public_process",
        "lead_agency": agency("Kentucky Cabinet for Economic Development", "https://newkentuckyhome.ky.gov/Locating_Expanding/KYoz", None, "(502) 564-7670"),
        "state_deadline": "2026-05-29",
        "scoring_rubric_url": "https://newkentuckyhome.ky.gov/Locating_Expanding/KYoz",
        "process": "Application (XLSX) and criteria guidance (DOCX) downloadable from state page. Deadline May 29, 2026. No online portal — file download and email submission. Webinar held March 3, 2026.",
        "notes": "Contacts: Deven Richardson (Director), Scott Moseley (Project Manager). 137 tracts to be nominated.",
    },
    "louisiana": {
        "status_tier": "contact_only",
        "lead_agency": agency("Louisiana Economic Development (LED)", "https://www.opportunitylouisiana.gov/incentive/federal-opportunity-zones"),
        "notes": "LED confirmed lead. No OZ 2.0 nomination process published.",
    },
    "maine": {
        "status_tier": "contact_only",
        "lead_agency": agency("Maine Dept. of Economic and Community Development (DECD)", "https://www.maine.gov/decd/business-development/financial-incentives-resources/opportunity-zones"),
        "notes": "DECD confirmed lead. No OZ 2.0 guidance published.",
    },
    "maryland": {
        "status_tier": "contact_only",
        "lead_agency": agency("Maryland Dept. of Housing and Community Development (DHCD) / MD Commerce", "https://dhcd.maryland.gov/pages/oz/opportunityzones.aspx"),
        "notes": "Dual-agency lead: DHCD + Commerce. Page addresses OZ 1.0 only. No OZ 2.0 guidance published.",
    },
    "massachusetts": {
        "status_tier": "contact_only",
        "lead_agency": agency("Massachusetts Office of Business Development (MOBD)", "https://www.mass.gov/opportunity-zone-program"),
        "notes": "MOBD confirmed lead. No OZ 2.0 application or deadline published.",
    },
    "michigan": {
        "status_tier": "contact_only",
        "lead_agency": agency("Michigan Economic Development Corporation (MEDC) / MSHDA", "https://www.michigan.gov/opportunityzones"),
        "notes": "Co-leads MEDC and MSHDA confirmed. No OZ 2.0 nomination portal or deadline published.",
    },
    "minnesota": {
        "status_tier": "contact_only",
        "lead_agency": agency("Minnesota Dept. of Employment and Economic Development (DEED)", "https://mn.gov/deed/opportunityzones/"),
        "notes": "DEED page explicitly states more information will be posted when the July 1, 2026 window opens. No application or deadline published.",
    },
    "mississippi": {
        "status_tier": "public_process",
        "lead_agency": agency("Mississippi Development Authority (MDA)", "https://mississippi.org/community-resources/opportunity-zones/", "tclimer@mississippi.org", "(601) 359-9387"),
        "state_deadline": "2026-05-31",
        "process": "Live public feedback form open through May 31, 2026. Four listening sessions held April–May across congressional districts. Contact: Tim T. Climer, PCED, Community and Rural Development.",
        "notes": "101 tracts to be nominated from 404 eligible. No formal scoring rubric published.",
    },
    "missouri": {
        "status_tier": "public_process",
        "lead_agency": agency("Missouri Dept. of Economic Development (DED)", "https://ded.mo.gov/programs/business-community/opportunity-zones", "OpportunityZones@ded.mo.gov"),
        "state_deadline": "2026-05-17",
        "application_portal_url": "https://modedfederalinitiatives.submittable.com/submit/e2490327-5b12-4d24-9c90-64092f51f7ad/missouri-opportunity-zones-2-0-program-intake-form",
        "process": "Submittable portal open April 7–May 17, 2026. DED reviews May–June, releases tentative recommendations for public comment in July, finalizes for governor in August, submits August, effective January 2027.",
        "notes": "131 tracts to be nominated from 523 eligible.",
    },
    "montana": {
        "status_tier": "contact_only",
        "lead_agency": agency("Montana Dept. of Commerce, Community Development Division", "https://commerce.mt.gov/Infrastructure-Planning/Resources/Opportunity-Zones/", None, "(406) 841-2700"),
        "notes": "Commerce page addresses OZ 1.0. Montana subject to 25-zone statutory minimum. No OZ 2.0 guidance published.",
    },
    "nebraska": {
        "status_tier": "public_process",
        "lead_agency": agency("Nebraska Dept. of Economic Development (DED)", "https://opportunity.nebraska.gov/programs/business/opportunity-zones/", "ded.opportunityzones@nebraska.gov", "(402) 471-3063"),
        "state_deadline": "2026-05-01",
        "process": "Application period ran March 2–May 1, 2026 (now closed). DED reviewing submissions for gubernatorial recommendation. Final selections announced after Treasury approval.",
        "notes": "Application window closed. 28 tracts to be nominated from 112 eligible.",
    },
    "nevada": {
        "status_tier": "contact_only",
        "lead_agency": agency("Nevada Governor's Office of Economic Development (GOED)", "https://goed.nv.gov/programs-incentives/opportunity-zones/", None, "(800) 336-1600"),
        "notes": "GOED confirmed lead. No OZ 2.0 nomination guidance published.",
    },
    "new-hampshire": {
        "status_tier": "contact_only",
        "lead_agency": agency("New Hampshire Dept. of Business and Economic Affairs (BEA)", "https://www.nheconomy.com/grow/opportunity-zones"),
        "notes": "BEA confirmed lead. Page addresses OZ 1.0 only. No OZ 2.0 process published.",
    },
    "new-jersey": {
        "status_tier": "contact_only",
        "lead_agency": agency("NJ Dept. of Community Affairs (DCA) / NJ Economic Development Authority (NJEDA)", "https://nj.gov/governor/njopportunityzones/"),
        "notes": "Resource center confirmed. No OZ 2.0 nomination process or deadline published.",
    },
    "new-mexico": {
        "status_tier": "public_process",
        "lead_agency": agency("New Mexico Economic Development Dept. (EDNM)", "https://www.edd.newmexico.gov/programs-and-services/communities/opportunity-zones/", "info@edd.nm.gov", "(505) 827-0300"),
        "state_deadline": "2026-07-01",
        "scoring_rubric_url": "https://www.edd.newmexico.gov/programs-and-services/communities/opportunity-zones/",
        "process": "Multi-phase COG-based process: Councils of Governments submit nominations to EDNM by May 15, 2026; EDNM reports to Governor by June 15; 65 tracts submitted to Treasury July 1. Scoring criteria published: development potential, local policies, infrastructure proximity.",
        "notes": "No online portal — COG-based submission process.",
    },
    "new-york": {
        "status_tier": "contact_only",
        "lead_agency": agency("Empire State Development (ESD)", "https://esd.ny.gov/opportunity-zones"),
        "notes": "ESD confirmed lead. Page addresses OZ 1.0 only. No OZ 2.0 nomination process published. 426 tracts to be nominated from 1,702 eligible.",
    },
    "north-carolina": {
        "status_tier": "public_process",
        "lead_agency": agency("North Carolina Department of Commerce", "https://www.commerce.nc.gov/data-tools-reports/opportunity-zones-north-carolina", "OZ-Feedback@commerce.nc.gov", "(919) 814-4600"),
        "state_deadline": "2026-06-07",
        "scoring_rubric_url": "https://www.commerce.nc.gov/data-tools-reports/opportunity-zones-north-carolina",
        "process": "Public feedback deadline June 7, 2026 at 11:59 p.m. Submissions via Excel form emailed to OZ-Feedback@commerce.nc.gov. Three published scoring criteria: Business Development & Job Creation, Strategic Local Revitalization, Pathways to Housing. ArcGIS mapping tool available.",
        "notes": "Contact: Emily Roach Pandich, Director of Policy and Strategic Planning. 202 tracts to be nominated.",
    },
    "north-dakota": {
        "status_tier": "contact_only",
        "lead_agency": agency("North Dakota Department of Commerce, Economic Development & Finance Division", None, None, "(701) 328-5344"),
        "notes": "Contact Rich Garman (Director) confirmed. No URL or OZ 2.0 guidance found. ND subject to 25-zone statutory minimum.",
    },
    "ohio": {
        "status_tier": "public_process",
        "lead_agency": agency("Ohio Department of Development (ODOD)", "https://www.greaterohio.org/opportunityzones"),
        "state_deadline": "2026-05-31",
        "process": "ODOD opened a 30-day online portal to accept local nominations in April 2026. Greater Ohio Policy Center provides technical assistance. Current OZ 1.0 designations are not automatically renewed.",
        "notes": "Portal URL (opportunityzones.ohio.gov) returned 404 at time of check. 258 tracts to be nominated from 1,032 eligible.",
    },
    "oklahoma": {
        "status_tier": "public_process",
        "lead_agency": agency("Oklahoma Department of Commerce", "https://www.okcommerce.gov/doing-business/business-relocation-expansion/incentives/federal-opportunity-zones/", "jon.chiappe@okcommerce.gov", "(405) 815-5210"),
        "application_portal_url": "https://forms.okcommerce.gov/260495603721860",
        "process": "Nomination form published April 10, 2026. Contacts: Jon Chiappe (405-815-5210) and Aldwyn Sappleton (405-815-5369). No formal deadline stated for community submissions.",
        "notes": "104 tracts to be nominated from 413 eligible; 188 qualify as rural.",
    },
    "oregon": {
        "status_tier": "public_process",
        "lead_agency": agency("Business Oregon", "https://www.oregon.gov/biz/programs/opportunity_zones/pages/default.aspx", "incentives.program@biz.oregon.gov", "(503) 986-0123"),
        "state_deadline": "2026-05-22",
        "application_portal_url": "https://www.oregon.gov/biz/programs/opportunity_zones/pages/default.aspx",
        "scoring_rubric_url": "https://www.oregon.gov/biz/programs/opportunity_zones/pages/default.aspx",
        "process": "RFA open with deadline May 22, 2026 at 5:00 p.m. PT. Scoring criteria: Project Viability & Investment Readiness, Local Support & Capacity, Strategic Alignment. Eligible applicants: cities, counties, ports, tribes, EDOs. Single application per tract.",
        "notes": "Tribal liaison: Brian Plinski (Brian.PLINSKI@biz.oregon.gov). 58 tracts to be nominated.",
    },
    "pennsylvania": {
        "status_tier": "contact_only",
        "lead_agency": agency("Pennsylvania Dept. of Community and Economic Development (DCED)", "https://dced.pa.gov/programs-funding/federal-funding-opportunities/qualified-opportunity-zones/", "oppzones@pa.gov"),
        "process": "Phased timeline published: spring 2026 stakeholder engagement, summer 2026 draft map, early fall 2026 state submission. Five priority sectors: housing, industrial sites, main street, rural, innovation. Webinars and public input method forthcoming.",
        "notes": "No portal open yet. Classifying contact_only because no submission mechanism is live. 217 tracts to be nominated.",
    },
    "rhode-island": {
        "status_tier": "contact_only",
        "lead_agency": agency("Rhode Island Commerce Corporation", "https://commerceri.com/site-selection/opportunity-zones/", None, "(401) 278-9100"),
        "notes": "Commerce RI confirmed lead. Website addresses OZ 1.0. Subject to 25-zone statutory minimum. No OZ 2.0 guidance published.",
    },
    "south-carolina": {
        "status_tier": "public_process",
        "lead_agency": agency("South Carolina Department of Commerce (SC Commerce)", "https://www.sccommerce.com/opportunity-zone", "oz@sccommerce.com"),
        "state_deadline": "2026-06-01",
        "application_portal_url": "https://www.sccommerce.com/opportunity-zone-submission",
        "process": "Community nomination deadline June 1, 2026. SC Commerce provides recommendations to Governor by July 15. Criteria: highest growth/economic impact potential, infrastructure, alignment with state economic strategy. Regional information meetings and virtual workshops offered.",
        "notes": "112 tracts to be nominated from 445 eligible.",
    },
    "south-dakota": {
        "status_tier": "contact_only",
        "lead_agency": agency("South Dakota Governor's Office of Economic Development (GOED)", None),
        "notes": "GOED presumed lead. No confirmed URL or OZ 2.0 guidance found. Subject to 25-zone statutory minimum.",
    },
    "tennessee": {
        "status_tier": "contact_only",
        "lead_agency": agency("Tennessee Dept. of Economic and Community Development (TNECD)", "https://www.tn.gov/ecd/opportunity-zones.html", "ED.OpportunityZones@tn.gov", "(615) 741-1888"),
        "notes": "TNECD held stakeholder discussion February 18, 2026. No OZ 2.0 application or deadline published as of 2026-05-05.",
    },
    "texas": {
        "status_tier": "public_process",
        "lead_agency": agency("Texas Economic Development & Tourism Office (EDT), Office of the Governor", "https://gov.texas.gov/business/page/opportunity-zones", "OppZone2.0@gov.texas.gov"),
        "state_deadline": "2026-06-26",
        "scoring_rubric_url": "https://gov.texas.gov/business/page/opportunity-zones",
        "process": "Community submission deadline June 26, 2026. EDT submits to Treasury by August 3, 2026. Downloadable Nomination Packet for EDOs and county judges. Four scoring criteria: statutory compliance, local support, project viability (24–48 month deployment), geographic balance (rural/disaster area preference).",
        "notes": "605 tracts to be nominated from 2,420 eligible.",
    },
    "utah": {
        "status_tier": "contact_only",
        "lead_agency": agency("Utah Governor's Office of Economic Opportunity (Go Utah)", "https://business.utah.gov/news/opportunity-awaits-statewide-opportunity-zones-announced/"),
        "notes": "Governor's office stated it is 'already working on how best to proceed.' No formal process published.",
    },
    "vermont": {
        "status_tier": "contact_only",
        "lead_agency": agency("Vermont Agency of Commerce and Community Development (ACCD)", "https://accd.vermont.gov/OpportunityZones"),
        "notes": "ACCD confirmed lead. All 24 eligible tracts can be nominated (statutory minimum applies). No OZ 2.0 process published.",
    },
    "virginia": {
        "status_tier": "contact_only",
        "lead_agency": agency("Virginia Economic Development Partnership (VEDP) / DHCD", "https://www.dhcd.virginia.gov/opportunity-zones-oz", "oz2026@vedp.org"),
        "notes": "Dual-agency lead. Webinars held April 16 and 21, 2026; stakeholder survey closed April 27. No formal application portal or scoring rubric. 152 tracts to be nominated.",
    },
    "washington": {
        "status_tier": "public_process",
        "lead_agency": agency("Washington State Department of Commerce", "https://www.commerce.wa.gov/opportunity-zones/", "Community.Engagement@Commerce.wa.gov"),
        "state_deadline": "2026-05-28",
        "application_portal_url": "https://www.commerce.wa.gov/funding/opportunity-zones-2-0-census-tract-designation-request-for-applications/",
        "scoring_rubric_url": "https://www.commerce.wa.gov/funding/opportunity-zones-2-0-census-tract-designation-request-for-applications/",
        "process": "RFA portal opened April 28, 2026. Deadline May 28, 2026. Scoring criteria PDF published. Q&A period closes May 21. Pre-proposal webinars May 7 (rural/non-rural and tribal). Recommendations due to Governor by June 30.",
        "notes": "99 tracts to be nominated.",
    },
    "west-virginia": {
        "status_tier": "contact_only",
        "lead_agency": agency("West Virginia Department of Economic Development", "https://westvirginia.gov/category/wv-opportunity-zones/"),
        "notes": "Confirmed lead. No OZ 2.0 guidance published.",
    },
    "wisconsin": {
        "status_tier": "contact_only",
        "lead_agency": agency("Wisconsin Economic Development Corporation (WEDC)", None),
        "notes": "WEDC presumed lead. No confirmed URL or OZ 2.0 guidance found.",
    },
    "wyoming": {
        "status_tier": "contact_only",
        "lead_agency": agency("Wyoming Business Council", "https://wyomingbusiness.org/business/financing/financial-incentives/opportunity-zones/"),
        "notes": "Contact: Connor Christensen, Economic Policy & Research Advisor, (307) 287-4709. No formal application or deadline. Explicitly states federal guidance still evolving.",
    },
}


def main():
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)

    updated = 0
    for slug, patch in PATCHES.items():
        if slug not in data:
            print(f"WARNING: {slug} not in YAML — skipping")
            continue
        for key, val in patch.items():
            if isinstance(val, dict) and isinstance(data[slug].get(key), dict):
                data[slug][key].update(val)
            else:
                data[slug][key] = val
        updated += 1

    with open(YAML_PATH, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    tiers = {}
    for entry in data.values():
        t = entry.get("status_tier", "unknown")
        tiers[t] = tiers.get(t, 0) + 1

    print(f"Patched {updated} states → {YAML_PATH}")
    for tier, count in sorted(tiers.items()):
        print(f"  {tier}: {count}")


if __name__ == "__main__":
    main()
