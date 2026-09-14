# Dell Wyse 5070 Extended: Dell documentation findings

Research date: 2026-09-14

## Confirmed external specifications

Dell's Wyse 5070 Extended Thin Client User Guide specifies:

| Dell dimension | Value |
|---|---:|
| Height | 184 mm |
| Width | 66 mm |
| Depth | 184 mm |
| Starting weight | 1.47 kg |

Source: [Dell, Physical specifications](https://www.dell.com/support/manuals/en-ca/wyse-5070-thin-client/5070_extd_ug/physical-specifications?guid=guid-5a72233b-732e-462f-997c-e9b983b350e3&lang=en-us)

Dell uses the normal vertical desktop orientation for these labels. For the proposed horizontal rack orientation, Dell's nominal 184 mm height becomes chassis width, 184 mm depth stays depth, and nominal 66 mm width becomes vertical thickness.

The owner's measured bare chassis is 184 x 184 x 55.9 mm, or 59.5 mm including feet. Therefore the 66 mm Dell width is not an appropriate cradle-contact dimension. It likely describes the shipped standing configuration or another maximum-envelope convention. Use the physical 55.9/59.5 mm measurements for fit and retain 66 mm only as a documented maximum-envelope cross-check.

## Variant identity

Dell maintains separate user guides for the Extended and standard Wyse 5070. The Extended guide describes the optional AMD E9173 graphics card and includes a PCIe slot in the chassis overview. The standard unit is substantially narrower: Dell specifies it as 184 x 35.6 x 184 mm and 1.13 kg. A rack model derived directly from standard-unit geometry therefore cannot fit the Extended chassis.

Sources:

- [Dell, Extended model introduction](https://www.dell.com/support/manuals/en-ca/wyse-5070-thin-client/5070_Extd_UG/Welcome-to-Dell-Wyse-5070-extended-thin-client?guid=guid-2ce4e19c-d7ee-4539-bf83-4b5994fda6c5&lang=en-us)
- [Dell, standard model physical specifications](https://www.dell.com/support/manuals/en-ca/wyse-5070-thin-client/5070_std_ug/Physical-specifications?guid=guid-23626e93-07d2-47a3-9c3d-d467c2f29db0&lang=en-us)

No Dell evidence found in the checked documentation identifies a different external chassis for a distinct "2022" revision. Treat 2022 as the unit's manufacture/configuration era, not a separate mechanical variant, unless its service tag documentation says otherwise.

## Chassis views and rack-design implications

Dell's official chassis overview contains a labeled composite front/rear image and identifies the interfaces that must remain unobstructed. The front includes the power button/light, optional CAC reader, USB ports, USB-C, and audio. The rear includes serial/parallel options, DisplayPort, network, power, expansion slot, antenna, security features, and power-cable hook. The image is useful for confirming which face is front, but it has no dimensional scale and cannot support precise port or vent coordinates.

- [Dell, chassis overview and labeled front/rear image](https://www.dell.com/support/manuals/en-ca/wyse-5070-thin-client/5070_extd_ug/chassis-overview?guid=guid-05cb3bb6-b6e8-4dca-96ff-17103019ab7c&lang=en-us)
- [Direct Dell chassis-overview image](https://dl.dell.com/topics/5070_extd_ug/images/GUID-6FF09B30-12F4-4E4C-AA85-4E98E04451D0-low.jpg)
- [Complete Dell Extended user-guide PDF](https://dl.dell.com/topicspdf/wyse-5070-thin-client_users-guide_en-us.pdf)

Dell lists P, E, U, Dual VESA, and VESA Wall mounts as supported accessories, and says the vertical stand ships with the client. The guide does not provide mounting-hole coordinates, foot coordinates, or rack-specific geometry. It also does not claim support for a horizontal 10-inch rack cradle.

Source: [Dell, Supported mounts](https://www.dell.com/support/manuals/en-ca/wyse-5070-thin-client/5070_extd_ug/supported-mounts?guid=guid-83f89eaf-c711-4656-b9df-6125e837cf52&lang=en-us)

## Design inputs supported by this research

- Use 184 mm for both body width and depth, matching both Dell and the owner's measurements.
- Use 55.9 mm for rigid-body height and 59.5 mm for occupied height with feet, based on direct measurement rather than Dell's 66 mm nominal envelope.
- Keep the complete front and rear faces open. Dell documents dense connector populations on both faces.
- Do not infer side-vent, foot, port, or mounting-hole coordinates from Dell's illustration. Use direct measurements or orthographic photographs for those features.
- Do not reuse the standard model's 35.6 mm thickness or retention geometry for the Extended chassis.
