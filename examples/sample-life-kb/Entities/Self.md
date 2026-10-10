---
type: "entity"
entity_type: "person"
core: false
aliases: []
---

# Self

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
