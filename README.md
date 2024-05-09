# Focal Lock for Blender 2.79

The "Focal Lock" add-on fork for Blender 2.79

Addon for Blender to maintain a camera's focal length/distance ratio.

Source: https://github.com/AnsonSavage/Focal_Lock

Current add-on version
-
1.3.1.

Blender versions
-
2.79

Location and call
-
The “Properties” area – "Data" tab - Focal Lock

Installation
-
- Download the *.zip archive with the add-on distributive.
- The “Preferences” window — Add-ons — Install… — specify the downloaded archive.

By
-
Nikita Akimov, Paul Kotelevets

Version history
-
1.3.3.
- Added option "Enabled for the scene". If checkbox is OFF - doesn't process Focal Lock work. If ON - Focal Lock works, but can high load CPU on week computers.

1.3.2.
- Fixed error if no cameras in the scene

1.3.1.
- Fixed formula from Shift X

1.3.0.
- Added the "Shift Lock" functional for "Shift X" parameter

1.2.1.
- Fixed issue with renamed cameras

1.2.0.
- Added the "Auto reset" checkbox. If it is on - when enabling the "Enable Lock" checkbox, for all other cameras the "Enable Lock" checkboxes are off (like pressing the "Clear All Other" button)

1.1.2.
- Try to return back button for clearing lock in all other cameras 

1.1.1.
- Operator for clearing other cameras replaced with option "Updated only for active camera" due to some issues with cameras properties recalculating 

1.1.0.
- Added operator for clearing focal lock option for all cameras except scene active 

1.0.2.
- Fixed issue with Track constraint

1.0.1.
- Interface moved to the "Data" tab
- Don't show interface if camera is not active

1.0.0.
- Forked
- Updated for Blender 2.79
