# Project skills

Claude Code loads the skills in this directory in sessions on this repository. They are development aids only: the plugin ships the skills in the top-level skills/ directory, not these.

| Skill | Purpose | Upstream | Licence |
|---|---|---|---|
| test-driven-development | Write a failing test before the implementation | [obra/superpowers](https://github.com/obra/superpowers) @ bb92a77 | MIT (LICENSE in the directory) |
| systematic-debugging | Find the root cause before fixing a bug | same | MIT (LICENSE in the directory) |
| verification-before-completion | Run the verification commands before claiming work is done | same | MIT (LICENSE in the directory) |
| skill-creator | Create, change and evaluate skills | [anthropics/skills](https://github.com/anthropics/skills) @ dbd4588 | Apache-2.0 (LICENSE.txt in the directory) |
| webapp-testing | Test local web pages with Playwright | same | Apache-2.0 (LICENSE.txt in the directory) |
| grill-me | Type /grill-me to start an interview; calls grilling | [mattpocock/skills](https://github.com/mattpocock/skills) @ 49dd158 | MIT (LICENSE in the directory) |
| grilling | Interview about a plan or idea in rounds along its design tree, with a recommended answer per question | same | MIT (LICENSE in the directory) |

## Maintenance

- The contents match upstream and are not edited here; systematic-debugging leaves out upstream's evaluation scenarios and authoring log; the LICENSE of grill-me and grilling is copied from the root of the upstream repository.
- Code scanning skips this directory (.github/codeql/codeql-config.yml).
- To update, copy the whole directory again from the upstream commit, keep the licence file and update the commit in the table.
- grill-me only calls grilling: update both together from the same upstream commit.
