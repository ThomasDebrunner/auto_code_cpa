from xml.etree import ElementTree
from collections import defaultdict


class Stage:
    def __init__(self, threshold):
        self.threshold = threshold
        self.features = []


class HaarFeature:
    def __init__(self, palpha, nalpha, top_left, width, height, threshold, rects):
        self.palpha = palpha
        self.nalpha = nalpha
        self.top_left = top_left
        self.width = width
        self.height = height
        self.threshold = threshold
        self.rects = rects


class Rect:
    def __init__(self, top_left, width, height, weight):
        self.top_left = top_left
        self.width = width
        self.height = height
        self.weight = weight


def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def parse_rect(str):
    vals = tuple((int(float(x)) for x in str.split(' ')))
    tlx, tly, w, h, s = vals
    return Rect((tlx, tly), w, h, s)


def parse_feature(xc, rects):
    threshold = [float(x) for x in xc['internalNodes'].split(' ')][-1]
    palpha, nalpha = tuple((float(x) for x in xc['leafValues'].split(' ')))
    width = max(rects, key=lambda x: x.width).width
    height = max(rects, key=lambda x: x.height).height
    top_left = min(rects, key=lambda x: sum(x.top_left)).top_left
    return HaarFeature(palpha, nalpha, top_left, width, height, threshold, rects)


def parse_xml(filename):
    c = etree_to_dict(ElementTree.parse(filename).getroot())['opencv_storage']['cascade']
    s = c['stages']['_']
    f = c['features']['_']
    del c

    stages = []
    l = 0
    for i in range(len(s)):
        xs = s[i]
        stage = Stage(float(xs['stageThreshold']))
        for j in range(len(xs['weakClassifiers']['_'])):
            xc = xs['weakClassifiers']['_'][j]

            rects = [parse_rect(xr) for xr in f[l]['rects']['_']]
            l += 1
            feature = parse_feature(xc, rects)
            stage.features.append(feature)
        stages.append(stage)
    return stages