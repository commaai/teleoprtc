#!/usr/bin/env python

import argparse
import asyncio
import dataclasses
import json
import logging

import aiortc
from aiortc.mediastreams import VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

from bodyrtc import WebRTCOfferBuilder, WebRTCAnswerBuilder
from bodyrtc.stream import StreamingOffer


async def async_input():
  return await asyncio.to_thread(input)


async def StdioConnectionProvider(offer: StreamingOffer) -> aiortc.RTCSessionDescription:
  print("-- Please send this JSON to server --")
  print(json.dumps(dataclasses.asdict(offer)))
  print("-- Press enter when the answer is ready --")
  raw_payload = await async_input()
  payload = json.loads(raw_payload)
  answer = aiortc.RTCSessionDescription(**payload)

  return answer


async def run_answer(args):
  streams = []
  while True:
    print("-- Please enter a JSON from client --")
    raw_payload = await async_input()

    payload = json.loads(raw_payload)
    offer = StreamingOffer(**payload)
    if args.input_video:
      player = MediaPlayer(args.input_video)
      video_tracks = [player.video() for _ in offer.video]
    else:
      player = None
      video_tracks = [VideoStreamTrack() for _ in offer.video]
    audio_tracks = []

    stream_builder = WebRTCAnswerBuilder(offer.sdp)
    for cam, track in zip(offer.video, video_tracks, strict=True):
      stream_builder.add_video_stream(cam, track)
    for track in audio_tracks:
      stream_builder.add_audio_stream(track)
    stream = stream_builder.stream()
    answer = await stream.start()
    streams.append(stream)

    print("-- Please send this JSON to client --")
    print(json.dumps({"sdp": answer.sdp, "type": answer.type}))

    await stream.wait_for_connection()


async def run_offer(args):
  stream_builder = WebRTCOfferBuilder(StdioConnectionProvider)
  for cam in args.cameras:
    stream_builder.offer_to_receive_video_stream(cam)
  stream_builder.add_messaging()
  stream = stream_builder.stream()
  _ = await stream.start()
  await stream.wait_for_connection()
  print("Connection established and all tracks are ready")

  tracks = [stream.get_incoming_video_track(cam, False) for cam in args.cameras]
  while True:
    try:
      frames = await asyncio.gather(*[track.recv() for track in tracks])
      for key, frame in zip(args.cameras, frames, strict=True):
        print("Received frame from", key, frame.time)
    except aiortc.mediastreams.MediaStreamError:
      return
    print("=====================================")


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(dest="command", required=True)

  offer_parser = subparsers.add_parser("offer")
  offer_parser.add_argument("cameras", metavar="CAMERA", type=str, nargs="+", default=["driver"], help="Camera types to stream")

  answer_parser = subparsers.add_parser("answer")
  answer_parser.add_argument("--input-video", type=str, required=False, help="Stream from video file instead")

  args = parser.parse_args()

  logging.basicConfig(level=logging.CRITICAL, handlers=[logging.StreamHandler()])
  logger = logging.getLogger("WebRTCStream")
  logger.setLevel(logging.DEBUG)

  loop = asyncio.get_event_loop()
  if args.command == "offer":
    loop.run_until_complete(run_offer(args))
  elif args.command == "answer":
    loop.run_until_complete(run_answer(args))
