# Rebar Diameter Estimation MVP (Rhino Python)

## Goal
Build the simplest internal tool to test viability of "click 2 points on STL mesh -> get bar diameter" with minimal manual work.

## Why Rhino Python for MVP
- Fastest to iterate in current Rhino workflow.
- No plugin packaging required yet.
- Easy to port to RhinoCommon C# plugin later if MVP succeeds.

## MVP Workflow
1. User selects mesh (STL imported in Rhino).
2. User clicks two points on the same rebar, 100-500 mm apart, avoiding crossings.
3. Script computes a mesh shortest path between the two picks.
4. Script samples section planes along that path at fixed spacing (e.g., 25 mm), each plane normal to local path tangent.
5. For each section:
   - Intersect plane with mesh.
   - Keep largest closed loop.
   - Compute area `A`.
   - Convert to equivalent diameter `D = sqrt(4A/pi)`.
6. Script returns:
   - Median diameter across stations (primary output).
   - IQR/spread (noise indicator).
   - Count/% of invalid stations.

## Basic Quality Rules (MVP)
A station is invalid if:
- No closed intersection loop is found.
- Multiple similar-size loops are found (possible fused bars).
- Diameter is outside user range (example 8-40 mm).

If invalid station ratio exceeds threshold (example 30%), script returns:
- "Low confidence: likely fusion/crossing in selected window."

## Output Format (MVP)
- `Estimated diameter: XX.X mm`
- `Variability (IQR): YY.Y mm`
- `Valid stations: N / M`
- `Confidence: High/Low`

## Success Criteria
MVP is successful if:
- Operator can measure one bar segment in < 10 seconds after 2 clicks.
- Results are close to manual slicing average (within practical tolerance).
- Tool reliably flags bad/fused windows instead of returning misleading numbers.

## Out of Scope for MVP
- Full automatic separation of all bars in network.
- Perfect handling of heavily fused bars.
- Skeletonization/voxel methods.
- Production UI/plugin packaging.

## Next Step After MVP
If this works, promote to RhinoCommon plugin with:
- One-click command UX.
- Visual station preview (green valid / red invalid).
- Batch measurement and CSV export.
