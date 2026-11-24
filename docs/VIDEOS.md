# Music videos

Two approved Grobie music videos, set to WARP978, are part of this release. Watch them on [SLOPCORE TV](https://slopcore.army/watch/tv/) and on X. The official character launch was announced in the [Release Announcement](https://x.com/IFFinance/status/2125133303015440417) thread; the videos followed in their own posts.

The masters are too large for a normal git tree. They are attached to the [v1.0.0 GitHub Release](https://github.com/Intense-Finance/Grobie/releases/tag/v1.0.0).

| Title | Length | Watch | Release file | Bytes | MD5 | SHA-256 |
|---|---|---|---|---:|---|---|
| *Fun, Fun, Fun* | 3:44 | [X](https://x.com/IFFinance/status/2125138181305585973) · [SLOPCORE TV](https://slopcore.army/watch/tv/#v=2125138181305585973) | `grobie-fun-fun-fun-master.mp4` | 163,298,439 | `a08500f1a11c9b483b1725c5092ddbc0` | `688c9ec3712b1bc5345100d23eacd49b842872b45ee08e53542ccc182af541ea` |
| *Fun, Fun, Fun (The Director's Cut)* | 4:12 | [X](https://x.com/IFFinance/status/2125165619393798504) · [SLOPCORE TV](https://slopcore.army/watch/tv/#v=2125165619393798504) | `grobie-fun-fun-fun-directors-cut-412-v2.mp4` | 170,187,866 | `65ff9e8e57f147145a15c74444d31de2` | `7443030284b7c0c9732af5f508edeec51f77fe1d89e6dd2d1e88ed35fc438195` |

Both of those files are the approved masters, left untouched.

## The 4:12 container note

When the Director's Cut was rendered for review, the 4:12 file received a container comment (a text tag in the file properties, not anything you see or hear while it plays) that still said "review copy — not approved." The picture and sound were later approved as they stand.

That original file is unchanged in this Release. A **new** file was written by stream copy only (no re-encode):

| File | Bytes | MD5 | SHA-256 |
|---|---:|---|---|
| `grobie-fun-fun-fun-directors-cut-412-v2-approved-tag.mp4` | 170,187,897 | `c14edf9993816bac2c949c2807d2d344` | `03df8d657e361e996fb871f505f1bf322dce658f992dd0d36277b68e9bceb143` |

The new file's container comment reads: `Fun, Fun, Fun (The Director's Cut), 4:12 v2 — INTENSE FINANCE, LLC / SLOPCORE TV`.

Decoded per-stream MD5 (`ffmpeg -f md5`) is identical between the original and the new file:

- Video: `5bb94beb60edb388dbccfe36e6634361`
- Audio: `68cc1dfb64e5ad250c47eebb172388d8`

Use either file for playback. Use the original if you want the exact approved-master bytes. Use the approved-tag file if you want the same picture and sound with a container note that matches the approval.

A failed earlier 4:12 encode is not part of this package and must not be published.

Checksums: [`../videos/SHA256SUMS`](../videos/SHA256SUMS), [`../videos/MD5SUMS`](../videos/MD5SUMS). All of these files are under GitHub's 2 GiB Release-asset limit.

The videos were assembled with `grobie-mv` ([`../tools/grobie-mv/`](../tools/grobie-mv/), MIT). The lyrics and cue sheet are CC0 1.0, in [`../character/v2-video-kit/extras/`](../character/v2-video-kit/extras/).
