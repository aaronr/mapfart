from flask import abort, request, render_template, jsonify, send_file
import psycopg2
import sys
import os
import time
import glob
import json
import re
import subprocess
import tempfile
import math

from utils.jsonp import jsonp
from shapely.geometry import shape
from shapely.ops import cascaded_union
from geojson import Feature, FeatureCollection, dumps

from shapely.wkb import loads

def fart_serve(fart_id):
    if request.method == 'GET':
        try:
            tf = open("/tmp/fart_"+fart_id+".png", "r")
            return send_file(tf, mimetype='image/png')
        except Exception, e:            
            abort(404)
    abort(404)

def fart_recent():
    if request.method == 'GET':
        try:
            search_dir = "/tmp/"
            files = filter(os.path.isfile, glob.glob(search_dir + "fart_*.png"))
            files.sort(key=lambda x: os.path.getmtime(x))
            files = [[os.path.splitext(os.path.basename(tf))[0],time.ctime(os.path.getmtime(tf))] for tf in files]
            return render_template("recent.html", files = files[-20:])            
            #return jsonify({'files':' '.join(f for f in files)})
        except Exception, e:            
            abort(404)
    abort(404)

# Yummy default farts
def fart_default():
    if request.method == 'POST':
        return fart()

# Override the srid
def fart_srid(srid):
    if request.method == 'POST':
        return fart(srid=srid)

# Override the srid and size
def fart_srid_xy(srid,xsize,ysize):
    if request.method == 'POST':
        return fart(srid=srid, xsize=xsize, ysize=ysize)

@jsonp
def fart(srid=4326, xsize=800, ysize=800):
    # Only POST is accepted
    if request.method == 'POST':
        data = request.data
        # Test code
        # return jsonify({'data': data, 'ct': request.environ['HTTP_CONTENT_TYPE']})

        # We recieved a GeoJSON payload
        if data.startswith('{'):
            try:
                js = json.loads(data)
                return process_geojson(js, srid, xsize, ysize)
            except Exception, e:            
                abort(404)
        # WKT Payload
        elif re.match(r'^[PLM\"]',data):
            # Strip off "'s if they are there
            if data.endswith("\""):
                data = data[:-1]
            if data.startswith("\""):
                data = data[1:]
            return process_wkt(data,xsize,ysize)
        # WKB Payload
        elif re.match(r'^[0-9A-F]+$',data.strip()):
            return process_wkb(data,xsize,ysize)

        else:
            # We dont know what this data is....
            # return jsonify({'unknown data': data})
            abort(500)

def process_wkb(data,xsize,ysize):
    try:
        wkbdata = loads(data.strip().decode("hex"))
        tf = tempfile.NamedTemporaryFile(prefix='fart_', suffix='.png',delete=False)
        cmd = "/usr/local/lib/geom-0.2/bin/geom draw -w %s -h %s -f %s -g '%s'" % (xsize, ysize, tf.name, wkbdata.wkt)
        # return jsonify({'cmd':cmd})
        
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        # wait for processing to finish
        stdout_value, stderr_value = proc.communicate()
        if stderr_value:
            # return jsonify({'stdout':stdout_value, 'stderr':sderr_value})
            # log.error('stderr_value: %s' % stderr_value)
            abort(500)
    except Exception, e:            
        # return jsonify({'stdout':stdout_value, 'stderr':sderr_value})
        abort(500)
    return "http://mapfart.com/" + os.path.splitext(os.path.basename(tf.name))[0] + "\n"
            


def process_wkt(data,xsize,ysize):
    try:
        tf = tempfile.NamedTemporaryFile(prefix='fart_', suffix='.png',delete=False)
        cmd = "/usr/local/lib/geom-0.2/bin/geom draw -w %s -h %s -f %s -g '%s'" % (xsize, ysize, tf.name, data)
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        # wait for processing to finish
        stdout_value, stderr_value = proc.communicate()
        if stderr_value:
            # return jsonify({'stdout':stdout_value, 'stderr':sderr_value})
            # log.error('stderr_value: %s' % stderr_value)
            abort(500)
    except Exception, e:            
        # return jsonify({'stdout':stdout_value, 'stderr':sderr_value})
        abort(500)
    return "http://mapfart.com/" + os.path.splitext(os.path.basename(tf.name))[0] + "\n"


def process_geojson(js, srid, xsize, ysize):
    shapes = []
    points = []
    lines = []
    polygons = []
    count = 0
    for f in js['features']:    
        count = count + 1
        myShape = shape(f['geometry'])
        shapes.append(myShape)
        if re.match(r'Point', myShape.geom_type) or re.match(r'MultiPoint', myShape.geom_type):
            myFeature = Feature(id=count,
                                geometry=myShape,
                                properties = {"name": "foo1"})
            points.append(myFeature)
        elif re.match(r'Line', myShape.geom_type) or re.match(r'MultiLine', myShape.geom_type):
            myFeature = Feature(id=count,
                                geometry=myShape,
                                properties = {"name": "foo2"})
            lines.append(myFeature)
        elif re.match(r'Polygon', myShape.geom_type) or re.match(r'MultiPolygon', myShape.geom_type):
            myFeature = Feature(id=count,
                                geometry=myShape,
                                properties = {"name": "foo3"})
            polygons.append(myFeature)
    bbox = cascaded_union(shapes).bounds

    if srid != 4326:
        if srid==3857 or srid==900913:
            ymin = bbox[1]
            ymax = bbox[3]
                    # for spherical mercator clamp to 85 deg north and south
            if ymin < -85.0:
                ymin = -85.0
            if ymax > 85.0:
                ymax = 85.0

        bbox = (bbox[0],ymin,bbox[2],ymax)
            
        # we must translate the bbox to the output projection
        connstring="dbname='projfinder' port=5432 user='mapfart' host='localhost' password='mapfart'"
        try:
            conn=psycopg2.connect(connstring)
            cursor=conn.cursor()
            sql = "select st_x(st_transform(st_geometryfromtext('POINT(%s %s)',4326),%s)) as xmin, st_y(st_transform(st_geometryfromtext('POINT(%s %s)',4326),%s)) as ymin, st_x(st_transform(st_geometryfromtext('POINT(%s %s)',4326),%s)) as xmax, st_y(st_transform(st_geometryfromtext('POINT(%s %s)',4326),%s)) as ymax" % (bbox[0],bbox[1],str(srid),bbox[0],bbox[1],str(srid),bbox[2],bbox[3],str(srid),bbox[2],bbox[3],str(srid))
            cursor.execute(sql)
            results = cursor.fetchone()                
            bbox_string = " ".join(str(b) for b in results)
        except Exception, e:            
            abort(500)
    else:
        bbox_string = " ".join(str(b) for b in bbox)
            
    # Monkey with the image size to get the aspect ratio about the same as the extent of the data
    data_aspect = ((bbox[2] - bbox[0])/2) / (bbox[3] - bbox[1])
    if data_aspect>=1:
        ysize = math.trunc(float(xsize) / data_aspect)
    else:
        xsize = math.trunc(float(ysize) * data_aspect)

    # Testing debug
    #return jsonify({'xsize':xsize, 'ysize':ysize, 'srid':srid})

    tf_points = tempfile.NamedTemporaryFile(prefix='fart_pt_', suffix='.json', delete=False)
    tf_lines = tempfile.NamedTemporaryFile(prefix='fart_ln_', suffix='.json', delete=False)
    tf_polygons = tempfile.NamedTemporaryFile(prefix='fart_poly_', suffix='.json', delete=False)
    layers_to_draw = ""
    if len(points) > 0:
        tf_points.write(dumps(FeatureCollection(points)))
        layers_to_draw = layers_to_draw + "points "
    if len(lines) > 0:
        tf_lines.write(dumps(FeatureCollection(lines)))
        layers_to_draw = layers_to_draw + "lines "
    if len(polygons) > 0:
        tf_polygons.write(dumps(FeatureCollection(polygons)))
        layers_to_draw = layers_to_draw + "polygons "
    tf_points.flush()
    tf_points.close()
    tf_lines.flush()
    tf_lines.close()
    tf_polygons.flush()
    tf_polygons.close()

    # Now that we have our bounds and up to 3 files (points, lines, polygons) we 
    # can have mapserver kick out an image.
    mapfile = render_template("mapfart.map", point_name = tf_points.name,
                              line_name = tf_lines.name,
                              polygon_name = tf_polygons.name,
                              srid = str(srid))
    tf_mapfile = tempfile.NamedTemporaryFile(prefix='fart_', suffix='.map', delete=False)
    tf_mapfile.write(mapfile)
    tf_mapfile.flush()
    tf_mapfile.close()
    
    tf_png = tempfile.NamedTemporaryFile(prefix='fart_', suffix='.png',delete=False)
    
    try:
        cmd = "/usr/local/bin/shp2img -m %s -o %s -l '%s' -s %s %s -e %s" % (tf_mapfile.name, tf_png.name, layers_to_draw.strip(), str(xsize), str(ysize), bbox_string)
        #return jsonify({'cmd':cmd})
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        # wait for processing to finish
        stdout_value, stderr_value = proc.communicate()
        if stderr_value:
            pass
            # return jsonify({'stdout':stdout_value, 'stderr':stderr_value})
            # log.error('stderr_value: %s' % stderr_value)
    except Exception, e:            
        abort(500)
    return "http://mapfart.com/" + os.path.splitext(os.path.basename(tf_png.name))[0] + "\n"



def testcurl():
    if request.method == 'POST':
        # data = request.form.keys()[0]
        data = request.data
        foo = ''
        if len(request.args) > 0 and request.args['foo']:
            foo = request.args['foo']
        return jsonify({'data':data, 'foo':foo})
    else:
        abort(404)

