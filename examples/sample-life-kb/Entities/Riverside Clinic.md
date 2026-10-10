---
type: "entity"
entity_type: "organisation"
core: false
aliases: ["Riverside"]
---

# Riverside Clinic

## Related files

```base
filters:
  and:
    - file.hasLink(this.file)
    - '!file.inFolder("Archive")'
    - '!file.inFolder("Entities")'
views:
  - type: table
    name: Related files
    order:
      - file.name
      - event_date
      - type
      - status
```
