# sabnzbd-postprocess-tdarr

## Intent

# Intended workflow

```
sabnzbd > tdarr > sonarr > emby
```

- sabnzbd outputs to a tdarr input folder per-library
- tdarr transcodes videos from input folder to output folder
- sonarr/radarr moves videos from tdarr output to library

# The problem

- sometimes files disappear mysteriously, cause unknown
 (suspect multi-file downloads, tdarr transcodes one file, sees no more, erases directory?)
- lots of empty folders left over
- subtitles/etc frequently missing
 (tdarr has various "move all files" options but I suspect those contribute to 'files disappear' in edge cases)
- sabnzbd collects completed downloads because junk/unimported files/folders still exist

# The solution

This project is a pair of post-processing scripts which can be used with sabnzbd.

- It uses tdarr-fork.py to spawn a separate, deatched Python thread (tdarr-transcode.py) for each download.
- It gathers files, and moves them in groups.
- It waits for all videos in a download to be transcoded.
- It uses hardlinks, so extra "copies" take no space.
- It moves all original files outside tdarr, after the transcode completes.
- It cleans up after itself.
- It logs to /config/logs/tdarr-transcode.log

## Expectations

Many things are hard-coded as they are either a) expected container layout for sabnzbd or b) my personal layout. Feel free to raise issue if you want to use this script in your deployment and I'll work with you.

The following must be true:

sabnzbd downloads go to `/<any>/in/<library>-staging`
tdarr library watches `/<any>/in/<library>`
tdarr outputs to `/<any>/out/<library>-staging`
*arr watches `/<any>/out/<library>`

`/<any>/in` and `/<any>/out` and paths within are all on the same mount. No Docker volumes per `in`/`out` or per-library.
(This is the weakest requirement and only requires some minor rewrite, but for now remains a requirement.)

This project is now a key cog in my workflow, not some abandoned little random idea. If it doesn't work, it may be set up incorrectly.
If it still doesn't work, it's likely in a way I haven't noticed, and I would prefer to have it brought to my attention. Don't worry about reaching out.

## Use

- Configure your stack as specified in Expectations
- Set `tdarr-fork.py` as a Post-Processing script for your Category in sabnzbd
- Manually clean up logs at /config/logs/tdarr-transcode-*.log

## Contributing

- For now this is a personal project, but issues are open if anyone wishes to actually use this.
- I'm not really looking for significant contributions as I don't want the scope of this to expand much currently.
- If you see a bug, feel free to PR a fix or just raise an issue. If you're not sure, raise an issue.
