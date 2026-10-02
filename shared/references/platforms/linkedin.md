# LinkedIn

What LinkedIn is as a medium, for a member account (a person, not a company page). A skill reads this file at the step that says "read the reference of the platform"; a script reads the same facts from `linkedin.json`, beside this file. What belongs to the tool that publishes (credentials, endpoints, errors) is in the provider, not here.

Every fact below came from a real task. "The limit the workbench enforces" marks a bound that is the workbench's own: it is what the runtime and the scripts refuse, and it was not checked against the platform's documentation. `not checked` marks a value that was used and never confirmed.

## A post

- A post is text with optional media. It needs text: a post with no text is refused.
- Text: at most 3,000 characters (the limit the workbench enforces).
- Media: at most one image per post. The image is a JPG, a PNG or a GIF of at most 8 MB (8,388,608 bytes; the limit the workbench enforces). A file is told by its first bytes, not by its name.
- A post image is portrait, 1080 x 1350 pixels (4:5).
- The platform does not hold a member's post for later: its member API has no scheduling. A post that must go out at a time is published at that time by a scheduled job, and a publisher asked to post "at" a future time refuses.
- The permission to publish as a member lasts 60 days and is not renewed without the person. A plan of posts that runs past that day fails at the slot, silently for the person, unless it is checked when the plan is approved.

## Links, hashtags and mentions

- A link goes in the first comment, not in the body, when the project's strategy or voice says so. The first comment is then the link with at most one short line. The link comes from the project's material, never from a guess; a post with no link has no first comment.
- First comment: at most 1,250 characters (the limit the workbench enforces). It is published right after the post, as a comment by the same member, and one approval covers both.
- Hashtags: as many as the project's voice guide allows.
- A hashtag or a mention written in a draft may not appear as a link once published: that depends on the publisher. With the publisher that ships, `#word` in ASCII becomes a hashtag and `@name` stays plain text, never a mention. The text the person approves is the one the publisher's dry run shows, not the draft.

## Comments and replies

- A member account cannot list the comments on its posts from outside: the platform's API answers 403 to a member's token (checked 2026-09-29). Comments are found through the platform's notification e-mails, or the person pastes them.
- The layout of those notification e-mails has not been verified on a real e-mail: from an e-mail only the comment link is trusted. Until it is verified, a pasted comment link, with the commenter's name and the text, is the way a comment comes in.
- "Copy link to comment" gives a link that carries the two identifiers a reply needs (checked on real links, 2026-09-30): `https://www.linkedin.com/feed/update/urn:li:activity:<post>?commentUrn=urn%3Ali%3Acomment%3A%28activity%3A<post>%2C<comment>%29&...`. Its `commentUrn` parameter is the comment, in the short form below. A `replyUrn` parameter, when present, is a reply, and `commentUrn` is then the top-level comment it sits under.
- Comments nest one level: a reply to a reply is posted under the top-level comment.
- A reply names the post and the comment it answers, by their identifiers.
- Reply: at most 1,500 characters (the limit the workbench enforces; the platform's documentation of its Comments API states no limit, read 2026-09-29). A comment's text is kept up to 3,000 characters when it is read.

## Identifiers

A post and a comment are named by a URN. A skill never builds, cuts or rewrites one: it passes the value it was given, to the publisher's `--post-id`, `--comment-id` and `--parent-comment-id`.

| Identifier | Shape |
|------------|-------|
| A post | `urn:li:share:<digits>`, `urn:li:ugcPost:<digits>` or `urn:li:activity:<digits>` |
| A comment | `urn:li:comment:(urn:li:activity:<post digits>,<comment digits>)`; the part before the comma is the post's thread, and may be a `share` or a `ugcPost` |
| A comment, in a copied link | the short form `urn:li:comment:(activity:<post digits>,<comment digits>)`, which stands for the full form above |

A key derived from an identifier (an idempotency key, a file name) is derived from the whole value, never from a part of it such as the digits after the comma: an identifier of another platform need not have that part.

## The address of a post

- `https://www.linkedin.com/feed/update/<post identifier>/`, for example `https://www.linkedin.com/feed/update/urn:li:share:<digits>/`. This is the address the publisher prints for a post it published.
- A post also has an address of the form `https://www.linkedin.com/posts/<slug>`.
- The host is `www.linkedin.com` or `linkedin.com`, exactly: a host that only ends in that name is another site. The scheme is `https`, and the address of a post carries no query and no fragment.

## A profile

- Cover: a profile photo covers the left of the cover on desktop. Keep roughly the first quarter of the width empty, and confirm it on a screenshot of the applied profile.
- Cover size: 1584 x 396 pixels, with the first 420 pixels kept empty, is the size pieces were made at (`not checked` against the platform's help page: confirm there, and label a secondary source as such).
- A handle cannot be looked up without signing in. Whether a name is taken on the platform is asked of the person, by the platform's name, and never guessed from a web search.
- A person exports their own profile from the profile page: "More", then "Save to PDF". Never scrape the platform.
- The export is a PDF with a sidebar and a main column. Sidebar sections: Contact, Top Skills, Languages, Certifications, Honors-Awards, Publications. Main sections: Summary, Experience, Education. The name, the headline and the location are the lines just before "Summary". A role's dates are a line `<Month> <year> - <Month> <year>`, or `- Present` for a current role. Each page ends in `Page <n> of <m>`. These are the titles of an export in English; an export in another language uses other titles.
- The Contact section, e-mail addresses and phone numbers of an export are personal data: they are dropped before anything is written.

## What can be read from outside

- Nothing of a member's own numbers: a member account cannot read its analytics or its comments through the API. Followers and impressions are asked of the person, once, and dated.
- No public lookup of a handle (see "A profile").
- What the person can give: the profile export, a copied comment link with the comment's text, and the numbers they see on their own pages.
