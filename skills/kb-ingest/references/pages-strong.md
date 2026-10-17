# Writing a topic page (strong tier)

A topic page tells what the library knows about one topic, newest first, and every statement on it rests on a card. In the strong tier you write the page; scripts/ingest.py check-page then checks that it cites every current card of the topic and nothing else. A page that fails is not written.

## Input

Every card of the topic, from the cards files (names.cards_dir) that hold one. Each card gives the conclusion, the quote with its link [[<sources_dir>/<source>#^pN]], the date and, when there is one, the event date. Cards of archived versions are not in the cards folder and must not appear.

## Shape

```markdown
# <topic>

<Two or three sentences on the current state: what is true now, by the newest cards.>

## <a subject within the topic>

- <date>: <statement> [[Sources/<source>#^pN]]
- <date>: <statement> [[Sources/<source>#^pN]]
```

- Group the cards by subject when there are more than a few; within a group, newest first (event date, else the source's date).
- When newer cards contradict older ones, say so in one line and cite both; never drop the older card, it is part of the record.
- Every statement ends with the link of the card it rests on, exactly as the card gives it. A statement resting on two cards cites both.

## Rules

1. Every current card of the topic is cited at least once. Leave none out because it seems minor.
2. Nothing is stated that no card holds: no background knowledge, no inference, no advice.
3. Links are copied, never built: a link that does not match a card's source and anchor fails the check.
4. Keep the card's wording close; change it only to join cards into readable sentences.
5. No other wiki links in the text than the source links and, when useful, topic links of the form [[<topics_dir>/<page>|<topic>]].

## When check-page fails

It prints two lists. unknown: links on your page that no current card of the topic holds; remove them or correct them to the card's link. missing: cards the page does not cite; add them. Change nothing else, then check again once.
