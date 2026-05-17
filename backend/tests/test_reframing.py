from app.services.reframing import CropTrack, _clamp_center, _rolling_average, average_crop_x


def test_rolling_average_smooths_spikes():
    values = [0.0, 100.0, 0.0, 100.0, 0.0]
    out = _rolling_average(values, window=3)
    assert all(0.0 <= v <= 100.0 for v in out)
    assert out[-1] != values[-1]


def test_clamp_keeps_crop_in_bounds():
    assert _clamp_center(-100, crop_width=200, frame_width=1000) == 100
    assert _clamp_center(2000, crop_width=200, frame_width=1000) == 900
    assert _clamp_center(500, crop_width=200, frame_width=1000) == 500


def test_average_crop_x_handles_empty_track():
    track = CropTrack(fps=5.0, width=1920, height=1080, crop_width=607, centers_x=[])
    assert average_crop_x(track) == (1920 - 607) // 2
