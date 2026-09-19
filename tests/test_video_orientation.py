from unittest.mock import Mock

import pytest
from libdatachannel import Description

from teleoprtc.stream import WebRTCBaseStream
from teleoprtc.tracks import TiciVideoStreamTrack


class VideoTrack(TiciVideoStreamTrack):
  async def recv(self):
    raise NotImplementedError


def offer(extension=None, mid="video"):
  media = Description.Video(mid, Description.Direction.RecvOnly)
  media.add_h264_codec(96)
  if extension:
    media.add_ext_map(Description.Entry.ExtMap(extension))
  desc = Description("", Description.Type.Offer)
  desc.add_media(media)
  return str(desc)


@pytest.mark.parametrize("extension,mid,expected", [
  ("7 urn:3gpp:video-orientation", "video", 7),
  ("3/recvonly urn:3gpp:video-orientation", "video", 3),
  ("4/sendrecv urn:3gpp:video-orientation", "video", 4),
  ("3/sendonly urn:3gpp:video-orientation", "video", 0),
  ("3/inactive urn:3gpp:video-orientation", "video", 0),
  ("3 urn:3gpp:video-orientation", "other", 0),
  ("3 urn:ietf:params:rtp-hdrext:sdes:mid", "video", 0),
  ("15 urn:3gpp:video-orientation", "video", 0),
  (None, "video", 0),
])
def test_negotiation(extension, mid, expected):
  media = Description.Video("video", Description.Direction.SendOnly)
  assert WebRTCBaseStream._negotiate_video_orientation(media, offer(extension, mid)) == expected
  assert ("urn:3gpp:video-orientation" in str(media)) == bool(expected)
  if expected:
    assert f"a=extmap:{expected}/sendonly urn:3gpp:video-orientation" in str(media)


@pytest.mark.parametrize("orientation,extension,expected", [
  (3, "7 urn:3gpp:video-orientation", 7),
  (3, None, 0),
  (0, "7 urn:3gpp:video-orientation", 0),
])
def test_packetizer_configuration(orientation, extension, expected):
  track = VideoTrack("road", 1/60)
  track.video_orientation = orientation
  stream = Mock()
  stream.outgoing_video_tracks = [track]
  stream.outgoing_audio_tracks = []
  stream._track_state = []
  stream._receiver_report_tracks = {}
  stream._make_video_media.return_value = (Description.Video("video", Description.Direction.SendOnly), 123, 96, "test")
  stream._negotiate_video_orientation = WebRTCBaseStream._negotiate_video_orientation
  WebRTCBaseStream._add_producer_tracks(stream, offer(extension))
  config = stream._track_state[0][2]
  assert config.video_orientation_id == expected
  assert config.video_orientation == (orientation if expected else 0)
