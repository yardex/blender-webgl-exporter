# --------------------------------------------------------------------------
# ***** BEGIN GPL LICENSE BLOCK *****
#
# Copyright (C) 2010 Dennis Ippel
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****
# --------------------------------------------------------------------------

bl_info = {
    "name": "WebGL Native formats (Javascript or JSON)",
    "author": "Dennis Ippel, John Villar",
    "blender": (2, 5, 7),
    "api": 35622,
    "location": "File > Import-Export",
    "description": "Import-Export WebGL data with materials",
    "warning": "",
    "wiki_url": "http://code.google.com/p/blender-webgl-exporter/",
    "tracker_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"}

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
    import imp
    if "io_export_webgl" in locals():
        imp.reload(io_export_ply)
        
#import Blender
#from Blender import *
import bpy
import os
#from Blender.BGL import *

from bpy.props import CollectionProperty, StringProperty, BoolProperty
from io_utils import ExportHelper

EVENT_NOEVENT = 1
EVENT_DRAW = 2
EVENT_EXIT = 3
EVENT_EXPORT = 4
EVENT_BROWSEFILE = 5

def export_scenejs(class_name, mesh):
    s = "var BlenderExport = {};\n"
    s += "BlenderExport.%s = function() {\n" % (class_name)
    s += "return SceneJS.geometry({\n"
    s += "type: \'%s\',\n" % (class_name)
    
    vertices = "vertices : ["
    indices = "indices : ["
    indexcount = 0;

    for f in mesh.faces:
        vertices += "[%.6f,%.6f,%.6f],[%.6f,%.6f,%.6f],[%.6f,%.6f,%.6f]," % (f.verts[0].co.x, f.verts[0].co.y, f.verts[0].co.z,f.verts[1].co.x, f.verts[1].co.y, f.verts[1].co.z,f.verts[2].co.x, f.verts[2].co.y, f.verts[2].co.z)
        indices += "[%i,%i,%i]," % (indexcount,indexcount+1,indexcount+2)
        indexcount += 3
    
    indices += "],\n";
    vertices += "],\n";

    s += vertices
    s += indices
    
    if(exp_normals == 1):
        s += "normals : ["
        for v in mesh.verts: 
            s += "[%.6f, %.6f, %.6f]," % (v.no.x, v.no.y, v.no.z)
    
        s += "],\n"
    if (mesh.vertexColors):
        s += "colors : ["
        for face in mesh.faces:
            for (vert, color) in zip(face.verts, face.col):
                s += "[%.6f,%.6f,%.6f,%.6f]," % ( color.r / 255.0, color.g / 255.0, color.b / 255.0, color.a / 255.0)
        s += "]\n"
    if (mesh.faceUV):
        s += "texCoords : ["
        for face in mesh.faces:
            s += "[%.6f,%.6f],[%.6f,%.6f],[%.6f,%.6f]," % (face.uv[0][0], face.uv[0][1], face.uv[1][0], face.uv[1][1], face.uv[2][0], face.uv[2][1])
                
        s += "]\n"
    
    s += "});\n};"
    
    return s

def export_scenejson(class_name, mesh):
    """Exports the current mesh as a JSON model.

    Developed by johnvillarzavatti [at] gmail [dot] com

    returns an escaped string valid for any JSON parser
    """
    mats = "\"m\":["
    
    mtemp = ""
    for m in mesh.materials:
        mat = "{"
        #flags = m.get_mode()
        shaders = ""
        
        if m.use_shadeless: #flags & Material.Modes['SHADELESS']:
            shaders += ',"fb"' # Fullbright
            
        if m.type == "HALO": #flags & Material.Modes['HALO']:
            shaders += ',"ha"' # Halo
            
        mtexs = m.texture_slots
        ts = ""
        for t_slot in mtexs:
            if (t_slot) and (t_slot.texture) and (t_slot.texture.type == "IMAGE"):
                t = t_slot.texture
                toks = t.image.filepath.split("\\")
                pipe = "" # Stages of the pipeline this texture is involved in
                if t_slot.use_map_color_diffuse: # Color modulation
                    pipe += ",tx_m"
                
                if t_slot.use_map_displacement: # Bump mapping
                    pipe += ",bump"
                    if shaders.find('"bm"')<0:
                        shaders += ',"bm"'
                        
                if t_slot.use_map_normal: # Bump mapping
                    pipe += ",norm"
                    if shaders.find('"nm"')<0:
                        shaders += ',"nm"'
                    
                ts += ',{"fn":"'+toks[-1]
                if len(pipe)>0:
                    ts +='","pipe":"'+pipe[1:]
                ts += '"}'

        mat += "\"shaders\":[" + shaders[1:] + "],"
        mat += "\"texs\":["+ts[1:]+"]"
        mat += "}"
        mtemp += ","+mat
    mats += mtemp[1:]
    mats += "]"
    
    # Init arrays for each material group
    a_verts = list()
    a_idxs = list()
    for x in range(len(mesh.materials)):
        a_verts.append("")
        a_idxs.append(0)
            
    a_norms = list()
    for x in range(len(mesh.materials)):
        a_norms.append("")
            
    a_indices = list()
    for x in range(len(mesh.materials)):
        a_indices.append("")

    a_uvs = list()
    for x in range(len(mesh.materials)):
        a_uvs.append("")
        
    a_vcs = list()
    for x in range(len(mesh.materials)):
        a_vcs.append("")
        
    # Now dump the faces
    for i, f in enumerate(mesh.faces):
        #t_indices = ""
        
        # Quads not supported
        for v_idx in f.vertices:
            v = mesh.vertices[v_idx]
            a_verts[f.material_index] += ",%.2f,%.2f,%.2f" % (-v.co[0], v.co[2], v.co[1])
            a_norms[f.material_index] += ",%.2f,%.2f,%.2f" % (-v.normal[0], v.normal[2], v.normal[1])
            #a_indices[f.mat] += ",%i" % (a_idxs[f.mat])
            #t_indices = ",%i%s" % (a_idxs[f.material_index], t_indices)
            a_indices[f.material_index] += ",%i" % a_idxs[f.material_index]
            a_idxs[f.material_index] += 1
            
        #a_indices[f.material_index] += t_indices
        
        if (mesh.uv_textures):
            uv = mesh.uv_textures[0]
            #for uv in f.uv_textures:
            tcs = uv.data[i].uv_raw
            
            #Quads not supported here
            a_uvs[f.material_index] += ",%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (tcs[0], tcs[1], tcs[2], tcs[3], tcs[4], tcs[5])
            
        # Currently not working because i don't use it -- john
        #if (mesh.vertexColors):
        #    for color in f.col:
        #        a_vcs[f.mat] += ",%.2f,%.2f,%.2f,%.2f" % ( color.r / 255.0, color.g / 255.0, color.b / 255.0, color.a / 255.0)
    
    # Now compact all face arrays into each material group
    indices = "\"f\":["
    p_indices = ""
    for a in a_indices:
        if len(a)>0:
            p_indices += ",[" + a[1:] + "]"
    indices += p_indices[1:] + "]"
    
    texcoords = "\"uvs\":["
    p_texcoords = ""
    for a in a_uvs:
        p_texcoords += ",[" + a[1:] + "]"
    texcoords += p_texcoords[1:]+"]"
    
    vertices = "\"v\":["
    p_vertices = ""
    for a in a_verts:
        p_vertices += ",[" + a[1:] + "]"
    vertices += p_vertices[1:]+"]"
    
    normals = "\"n\":["
    p_normals = ""
    for a in a_norms:
        p_normals += ",[" + a[1:] + "]"
    normals += p_normals[1:]+"]"
    
    p_vcols = ""
    for a in a_vcs:
        if len(a)>0:
            p_vcols += ",[" + a[1:] + "]"
    if len(p_vcols)>0:
        vcols = "\"vcs\":[" + p_vcols[1:] + "]"
    else:
        vcols = ""
    
    # Now build our output
    s = "{"+vertices + ","
    s += normals + ","
    s += indices + ","
    s += texcoords + ","
    if (len(vcols) > 0):
        s += vcols + ","
    s += mats
    
    s += "}"
    
    return s

def export_objectJson(ob, me):
    obj = "{\"name\":\""+ob.name+"\","
    
    #ipo = ob.getIpo()
    ipo = None
   
    #print ob.matrix_local
    #obj += "\"mtx\":[[%.4f,%.4f,%.4f,%.4f],[%.4f,%.4f,%.4f,%.4f],[%.4f,%.4f,%.4f,%.4f],[%.4f,%.4f,%.4f,%.4f]]," % (ob.matrix_local[0][0], ob.matrix_local[0][1], ob.matrix_local[0][2], ob.matrix_local[0][3], ob.matrix_local[1][0], ob.matrix_local[1][1], ob.matrix_local[1][2], ob.matrix_local[1][3], ob.matrix_local[2][0], ob.matrix_local[2][1], ob.matrix_local[2][2], ob.matrix_local[2][3], ob.matrix_local[3][0], ob.matrix_local[3][1], ob.matrix_local[3][2], ob.matrix_local[3][3])
    obj += "\"mtx\":[[%.4f,%.4f,%.4f,%.4f],[%.4f,%.4f,%.4f,%.4f],[%.4f,%.4f,%.4f,%.4f],[%.4f,%.4f,%.4f,%.4f]]," % (ob.matrix_local[0][0], ob.matrix_local[1][0], ob.matrix_local[2][0], ob.matrix_local[3][0], ob.matrix_local[0][1], ob.matrix_local[1][1], ob.matrix_local[2][1], ob.matrix_local[3][1], ob.matrix_local[0][2], ob.matrix_local[1][2], ob.matrix_local[2][2], ob.matrix_local[3][2], ob.matrix_local[0][3], ob.matrix_local[1][3], ob.matrix_local[2][3], ob.matrix_local[3][3])
    #obj += "\"x\":%.4f,\"y\":%.4f,\"z\":%.4f,\"rx\":%.4f,\"ry\":%.4f,\"rz\":%.4f," % (ob.LocX, ob.LocZ, -ob.LocY, ob.RotX, ob.RotZ, ob.RotY)
    
    if ipo is not None:
        ipos = ""
    
        for crv in ipo.curves:
            ipos += ",{\"curve\":\"%s\",\"emode\":%i,\"imode\":%i,\"bezs\":[" % (crv.name, crv.extend, crv.interpolation)
            bzs = ""
            for bp in crv.bezierPoints:
                h1, p, h2 = bp.vec
                bzs += ",%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (h1[0], h1[1], p[0], p[1], h2[0], h2[1])
                #bzs += ",%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % (h1[0], h1[1], h1[2], p[0], p[1], p[2], h2[0], h2[1], h2[2])
            ipos += bzs[1:]+"]}"
    
        obj += "\"ipos\":[" + ipos[1:] + "],"
    
    obj += "\"mesh\":" + export_scenejson(ob.name.replace(".", ""), me)
    
    obj += "}"
    
    return obj
        
def export_native(class_name, mesh, ob):
    s = "var BlenderExport = {};\n"
    s += "BlenderExport.%s = {};\n" % (class_name)
    
    vertices = "BlenderExport.%s.vertices = [" % (class_name)
    indices = "BlenderExport.%s.indices = [" % (class_name)
    indexcount = 0;
    
    for f in mesh.faces:
        vertices += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.verts[0].co.x, f.verts[0].co.y, f.verts[0].co.z,f.verts[1].co.x, f.verts[1].co.y, f.verts[1].co.z,f.verts[2].co.x, f.verts[2].co.y, f.verts[2].co.z)
        indexcount += 3
    
    indices += "];\n";
    vertices += "];\n";

    s += vertices
    s += indices
    
    s += "for(var i=0;i<%s;i++) BlenderExport.%s.indices.push(i);\n" % (indexcount, class_name)
    
    if(exp_normals == 1):
        s += "BlenderExport.%s.normals = [" % (class_name)
        for v in mesh.verts: 
            s += "%.6f, %.6f, %.6f," % (v.no.x, v.no.y, v.no.z)
    
        s += "];\n"
    if (mesh.vertexColors):
        s += "BlenderExport.%s.colors = [" % (class_name)
        for face in mesh.faces:
            for (vert, color) in zip(face.verts, face.col):
                s += "%.6f,%.6f,%.6f,%.6f," % ( color.r / 255.0, color.g / 255.0, color.b / 255.0, color.a / 255.0)
        s += "];\n"
    if (mesh.faceUV):
        s += "BlenderExport.%s.texCoords = [" % (class_name)
        for face in mesh.faces:
            s += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (face.uv[0][0], face.uv[0][1], face.uv[1][0], face.uv[1][1], face.uv[2][0], face.uv[2][1])
        s += "];\n"

    if animation_button.val:
        s += "BlenderExport.%s.frames = [" % (class_name)
        matrix = ob.getMatrix('worldspace')

        for frame in xrange(animation_start.val, animation_end.val):
            Blender.Set('curframe', frame)
            tmpMesh = Mesh.New()
            tmpMesh.getFromObject(ob.name)
            tmpMesh.transform(matrix)
            s+= "["
            for f in tmpMesh.faces:
                for v in f.verts:
                    s += "%.6f,%.6f,%.6f," % (v.co.x, v.co.y, v.co.z)
            
            s += "],"
        s += "];"
    
    return s

def export_glge_js(class_name, mesh):
    s = "var BlenderExport = {};\n"
    s += "BlenderExport.%s = function() {\n" % (class_name)
    s += "var obj=new GLGE.Object(\'%s\');\n"  % (class_name)
    s += "var mesh=new GLGE.Mesh();\n" 
    vertices = "mesh.setPositions(["
    normals = "mesh.setNormals(["
    uvs = "mesh.setUV(["
    indices = "mesh.setFaces(["
    indexcount = 0;
    for f in mesh.faces:
        vertices += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.verts[0].co.x, f.verts[0].co.y, f.verts[0].co.z,f.verts[1].co.x, f.verts[1].co.y, f.verts[1].co.z,f.verts[2].co.x, f.verts[2].co.y, f.verts[2].co.z)
        if (f.smooth):
            normals += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.verts[0].no.x, f.verts[0].no.y, f.verts[0].no.z,f.verts[1].no.x, f.verts[1].no.y, f.verts[1].no.z,f.verts[2].no.x, f.verts[2].no.y, f.verts[2].no.z)
        else:
            normals += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.no.x, f.no.y, f.no.z,f.no.x, f.no.y, f.no.z,f.no.x, f.no.y, f.no.z)
        if (mesh.faceUV):
            uvs += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.uv[0][0], f.uv[0][1], f.uv[1][0], f.uv[1][1], f.uv[2][0], f.uv[2][1])
        indices += "%i,%i,%i," % (indexcount,indexcount+1,indexcount+2)
        indexcount += 3
        
    indicies=indices[:len(indices)-1]
    normals=normals[:len(normals)-1]
    if (mesh.faceUV):
        uvs=uvs[:len(uvs)-1]
    vertices=vertices[:len(vertices)-1]
    
    indices += "]);\n";
    normals += "]);\n";
    uvs += "]);\n";
    vertices += "]);\n";
    
    s += vertices
    s += normals
    if (mesh.faceUV):
        s += uvs
    s += indices
    
    s += "var material=new GLGE.Material();\n"
    s += "obj.setMaterial(material);\n"
    s += "obj.setMesh(mesh);\n"
    s += "return obj;\n};"
    print(s)
    return s
    
def export_glge_xml(class_name, mesh):
    s = "<?xml version=\"1.0\" ?>\n"
    s += "<glge>\n"
    s += "<mesh id=\"%s\">\n"  % (class_name)
    vertices = "<positions>"
    normals = "<normals>"
    uvs = "<uv1>"
    indices = "<faces>"
    indexcount = 0;
    
    for f in mesh.faces:
        vertices += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.verts[0].co.x, f.verts[0].co.y, f.verts[0].co.z,f.verts[1].co.x, f.verts[1].co.y, f.verts[1].co.z,f.verts[2].co.x, f.verts[2].co.y, f.verts[2].co.z)
        if (f.smooth):
            normals += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.verts[0].no.x, f.verts[0].no.y, f.verts[0].no.z,f.verts[1].no.x, f.verts[1].no.y, f.verts[1].no.z,f.verts[2].no.x, f.verts[2].no.y, f.verts[2].no.z)
        else:
            normals += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.no.x, f.no.y, f.no.z,f.no.x, f.no.y, f.no.z,f.no.x, f.no.y, f.no.z)
        #if (mesh.faceUV):
            #uvs += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.uv[0][0], f.uv[0][1], f.uv[1][0], f.uv[1][1], f.uv[2][0], f.uv[2][1])
        indices += "%i,%i,%i," % (indexcount,indexcount+1,indexcount+2)
        indexcount += 3
    
    if len(mesh.getUVLayerNames()):
        uvs = ""
        uvlcount = 0
        for uvlayer in mesh.getUVLayerNames():
            uvlcount = uvlcount + 1
            print("uvlayer " + uvlayer)
            mesh.activeUVLayer = uvlayer
            uvs += "<uv" + str(uvlcount) + ">"
            
            for f in mesh.faces:
                uvs += "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," % (f.uv[0][0], f.uv[0][1], f.uv[1][0], f.uv[1][1], f.uv[2][0], f.uv[2][1])    
                
            uvs=uvs[:len(uvs)-1]
            uvs += "</uv" + str(uvlcount) + ">\n"    
        
    indices=indices[:len(indices)-1]
    normals=normals[:len(normals)-1]
    vertices=vertices[:len(vertices)-1]
    
    indices += "</faces>\n";
    normals += "</normals>\n";
    vertices += "</positions>\n";
    
    s += vertices
    s += normals
    if (mesh.faceUV):
        s += uvs
    s += indices
    
    s += "</mesh>\n"
    s += "</glge>"
    
    return s

def event(evt, val):
    if (evt == Draw.QKEY and not val):
        Draw.Exit()

def bevent(evt):
    global EVENT_NOEVENT,EVENT_DRAW,EVENT_EXIT
    
    if (evt == EVENT_EXIT):
        Draw.Exit()
    elif (evt== EVENT_DRAW):
        Draw.Redraw()
    elif (evt== EVENT_EXPORT):
        sce = bpy.data.scenes.active
        
        obs = None
        
        if(exp_all == 1):
            # export all scene objects
            obs = [ob for ob in sce.objects if ob.type == 'Mesh']
        else:
            # export the selected objects
            obs = [ob for ob in sce.objects.selected if ob.type == 'Mesh']
        
        if (len(obs) == 0):
            Draw.PupMenu("Nothing to export. Please select a Mesh.")
            Draw.Exit()
            return
        
        singleFile = 0
        if(engine_menu.val == 6):
            singleFile = 1
            out = open(file_button.val, 'w')
            scn = Scene.GetCurrent()
            context = scn.getRenderingContext()
            data_string = "{\"scene\":1,\"fps\":%i,\"objs\":[" % (context.fps)
            comaSeparate = 0;
            
        # export all object names
        for ob in obs:
            me = Mesh.New()
            me.getFromObject(ob,0)
            class_name = ob.name.replace(".", "")
            
            if (not singleFile):
                ext = ""
            
            if (not singleFile):
                if(engine_menu.val ==4):
                    ext = ".xml"
                else:
                    ext = ".js"
                out = open(file_button.val+""+class_name+ext, 'w')
                data_string = ""

            if (engine_menu.val == 1):
                data_string = export_native(class_name, me, ob)
            elif(engine_menu.val == 2):
                data_string = export_scenejs(class_name, me)
            elif(engine_menu.val == 3):
                data_string = export_glge_js(class_name, me)
            elif(engine_menu.val == 4):
                data_string = export_glge_xml(class_name, me)
            elif(engine_menu.val == 5):
                data_string = export_copperlicht(class_name, me)
            elif(engine_menu.val == 6):
                # Fix this: must include object's IpoCurves
                #data_string = data_string+export_scenejson(class_name, me)
                if (not comaSeparate):
                    comaSeparate = 1
                else:
                    data_string = data_string + ","
                data_string = data_string+export_objectJson(ob)

            if (not singleFile):
                out.write(data_string)
                out.close()
        
        if (singleFile):
            out.write(data_string+"]}")
            out.close()
            
        Draw.PupMenu("Export Successful")
    elif (evt== EVENT_BROWSEFILE):
        if (engine_menu.val == 4):
            Window.FileSelector(FileSelected,"Export .xml", exp_file_name)
        elif (engine_menu.val == 6):
            Window.FileSelector(FileSelected,"Export .json", exp_file_name)
        else:
            Window.FileSelector(FileSelected,"Export .js", exp_file_name)
        Draw.Redraw(1)

def FileSelected(file_name):
    global file_button
    
    if file_name != '':
        file_button.val = file_name
    else:
        cutils.Debug.Debug('ERROR: filename is empty','ERROR')

def draw():
    global file_button, exp_file_name, animation_button, animation_start, animation_end
    global engine_menu, engine_name, exp_normals, exp_all
    global EVENT_NOEVENT, EVENT_DRAW, EVENT_EXIT, EVENT_EXPORT
    exp_file_name = ""

    glClear(GL_COLOR_BUFFER_BIT)
    glRasterPos2i(40, 240)

    engine_name = "Native WebGL%x1|SceneJS%x2|GLGE JS%x3|GLGE XML%x4|JSON%x6"
    engine_menu = Draw.Menu(engine_name, EVENT_NOEVENT, 40, 100, 200, 20, engine_menu.val, "Choose your engine")

    file_button = Draw.String('File location: ', EVENT_NOEVENT, 40, 70, 250, 20, file_button.val, 255) 
    Draw.PushButton('...', EVENT_BROWSEFILE, 300, 70, 30, 20, 'browse file')
    exp_normals = Draw.Toggle('Export normals', EVENT_NOEVENT, 250, 45, 100, 20, exp_normals.val)
    
    anim_down = 0
    
    if animation_button.val == 1:
        anim_down = 1
    
    animation_button = Draw.Toggle('Export animation frames (native WebGL only)', EVENT_NOEVENT, 400, 70, 300, 20, animation_button.val, 'Export keyframe animation')
    animation_start = Draw.Number('Start frame', EVENT_NOEVENT, 400, 45, 160, 20, animation_start.val, 1, 9999)
    animation_end = Draw.Number('End frame', EVENT_NOEVENT, 400, 20, 160, 20, animation_end.val, 2, 9999)
    
    exp_all = Draw.Toggle('Export ALL scene objects', EVENT_NOEVENT, 40, 45, 200, 20, exp_all.val)
    
    Draw.Button("Export",EVENT_EXPORT , 40, 20, 80, 18)
    Draw.Button("Exit",EVENT_EXIT , 140, 20, 80, 18)
    
def save(operator, context, filepath="", frame_start=1, frame_end=300, fps=25):
    print("nada aun")
    
def savejson(operator, context, filepath="", use_modifiers=True, use_normals=True, use_uv_coords=True, use_colors=True):
    sce = bpy.data.scenes[0]

    obs = [ob for ob in sce.objects if (ob.type == 'MESH') and (ob.select)]

    # if nothing is selected, export everything
    if len(obs) == 0:
        obs = [ob for ob in sce.objects if ob.type == 'MESH']
    
    data_string = "{\"scene\":1,\"fps\":%i,\"objs\":[" % (25) # Fixed for now
    
    ob_string = ""
    for ob in obs:
        me = ob.to_mesh(sce, True, "PREVIEW")
        ob_string = "%s,%s" % (ob_string, export_objectJson(ob, me))
        
    data_string = "%s%s]}" % (data_string, ob_string[1:])
    
    with open(filepath, 'wb') as file:
        file.write(data_string.encode('utf-8'))

    return "FINISHED"

class ExportWebgl(bpy.types.Operator, ExportHelper):
    '''Export objects as a WebGL object with normals and texture coordinates.'''
    bl_idname = "export_scene.webgl_js"
    bl_label = "Export WebGL"

    filename_ext = ".js"
    filter_glob = StringProperty(default="*.js", options={'HIDDEN'})

    use_modifiers = BoolProperty(name="Apply Modifiers", description="Apply Modifiers to the exported mesh", default=True)
    use_normals = BoolProperty(name="Normals", description="Export Normals for smooth and hard shaded faces", default=True)
    use_uv_coords = BoolProperty(name="UVs", description="Exort the active UV layer", default=True)
    use_colors = BoolProperty(name="Vertex Colors", description="Exort the active vertex color layer", default=True)

    def execute(self, context):
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        return save(self, context, **self.as_keywords(ignore=("check_existing", "filter_glob")))

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, "use_modifiers")
        row.prop(self, "use_normals")
        row = layout.row()
        row.prop(self, "use_uv_coords")
        row.prop(self, "use_colors")

class ExportJSON(bpy.types.Operator, ExportHelper):
    '''Export objects as a JSON object with normals and texture coordinates.'''
    bl_idname = "export_scene.webgl_json"
    bl_label = "Export JSON"

    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})

    use_modifiers = BoolProperty(name="Apply Modifiers", description="Apply Modifiers to the exported mesh", default=True)
    use_normals = BoolProperty(name="Normals", description="Export Normals for smooth and hard shaded faces", default=True)
    use_uv_coords = BoolProperty(name="UVs", description="Exort the active UV layer", default=True)
    use_colors = BoolProperty(name="Vertex Colors", description="Exort the active vertex color layer", default=True)

    def execute(self, context):
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        return savejson(self, context, **self.as_keywords(ignore=("check_existing", "filter_glob")))

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.prop(self, "use_modifiers")
        row.prop(self, "use_normals")
        row = layout.row()
        row.prop(self, "use_uv_coords")
        row.prop(self, "use_colors")
        

def menu_func_export(self, context):
    self.layout.operator(ExportWebgl.bl_idname, text="WebGL (.js)")
    self.layout.operator(ExportJSON.bl_idname, text="WebGL JSON (.json)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()