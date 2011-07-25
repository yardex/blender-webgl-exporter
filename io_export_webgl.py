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
        
import bpy
import os

from bpy.props import CollectionProperty, StringProperty, BoolProperty
#from io_utils import ExportHelper
from bpy_extras.io_utils import ExportHelper
import struct
import base64
import binascii
import json
from functools import reduce

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

def to_fixed16(flt):
    i_part = abs(int(flt))
    d_part = int(abs(flt - i_part)*256) & 255
    
    result = (i_part << 8) | d_part
    
    if flt < 0:
        result = -result
        
    return result
    
def export_animdata(ob, scene):
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    
    frames = []
    
    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        me = ob.to_mesh(scene, True, 'PREVIEW')
        
        numverts = len(me.vertices)
        
        frames.append(struct.pack(">%dh" % (numverts * 3), *[to_fixed16(ax) for v in me.vertices for ax in v.co]))
        
    return base64.encodebytes(bytes().join(frames)).decode('ascii')[:-1]
        
def export_objectJson(ob, me, scene):
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
    
    obj = "".join([obj, ",\"anim_data\": \"", export_animdata(ob, scene), "\""])
    
    obj += "}"
    
    return obj
    
def object_to_dict(scene, object, binary=False):
    outp = {'name': object.name}
    
    armature = object.find_armature()
    if armature is not None:
        # Put the armature in REST position
        armature_proper = bpy.data.armatures[armature.name]
        #armature.pose_position = 'REST'
        
    # Convert all the mesh's faces to triangles
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.context.scene.update()
    bpy.ops.object.mode_set(mode='OBJECT') # set it in object
    
    me = object.to_mesh(scene, True, "PREVIEW")
    reduce(lambda x,y: max(x,y), [grp.group for v in me.vertices for grp in v.groups])
    ome = {}
    
    numverts = len(me.vertices)
    numfaces = len(me.faces)
    
    # Binary mode packs everything as 16-bit fixed point big-endian arrays, 
    # taking the absolute value of the floating point original value, the first
    # 8 bits are the decimal part, last 8 bits are the integral part and then
    # the sign is swaped if necessary. UVs are packed differently, to obtain
    # your original approximated UV take the 16-bit int of each coord and divide
    # it by 8192.0f (keeps sign). Vertex groups are packed with the 10 less
    # significative bits taking the weight in the range (0 <= weight <= 1)*1023
    # and the 6 most significative bits as the vertex group. Each group is
    # preceded by a byte specifying how much groups follow it.
    # Everything gets Base64 encoded in binary mode.
    # Think of JSON as a binary-safe transport in this mode.
    #
    # Normal mode is the least efficient space-wise but is far more readable.
    #
    # Arrays are 'flattened' in both cases.
    if binary:
        fixed_proc = lambda x: to_fixed16(x)
        fixed_pack = lambda arr: base64.encodebytes(struct.pack(">%dh" % len(arr), *arr)).decode('ascii')[:-1]
        v_co_proc, v_co_pack = fixed_proc, fixed_pack
        v_normal_proc, v_normal_pack = fixed_proc, fixed_pack
        v_face_pack = fixed_pack
        v_uv_proc = lambda x: int(8192.0 * x)
        v_uv_pack = fixed_pack
        v_bw_proc = lambda x: ((x[0] & 63) << 10) | (int(x[1] * 1023.0) & 1023)
        v_bw_pack = lambda x: base64.encodebytes(bytes().join([struct.pack(">B%iH" % len(y), len(y), *y) for y in x])).decode('ascii')[:-1]
    else:
        identity = lambda i: i
        v_co_proc, v_co_pack = identity, identity
        v_normal_proc, v_normal_pack = identity, identity
        v_face_pack = identity
        v_uv_proc, v_uv_pack = identity, identity
        v_bw_proc, v_bw_pack = identity, identity
        
    ome['v'] = v_co_pack([v_co_proc(ax) for v in me.vertices for ax in v.co])
    ome['n'] = v_normal_pack([v_normal_proc(ax) for v in me.vertices for ax in v.normal])
    ome['f'] = v_face_pack([idx for f in me.faces for idx in f.vertices])
    
    ome['uv'] = []
    for layer in me.uv_textures:
        ome['uv'].append(v_uv_pack([v_uv_proc(st) for tex_face in layer.data for uv in tex_face.uv for st in uv]))
    
    if armature is not None:
        ome['bw'] = v_bw_pack([[v_bw_proc((grp.group, grp.weight)) for grp in v.groups] for v in me.vertices])

        # Put the armature in POSE position
        #armature.pose_position = 'POSE'
        
        #ome['b'] =
    else:
        # Export vertex animations
        pass
        
    outp['mesh'] = ome
    
    return outp
    
def export_scene_json(scene, binary=False):
    outp = {'scene': scene.name, 'fps': scene.render.fps}
    
    outp['objs'] = [object_to_dict(scene, obj, binary) for obj in scene.objects if (obj.type == 'MESH') and (obj.select)]
    
    return json.dumps(outp)

def savejson(operator, context,
    filepath="",
    use_modifiers=True,
    use_normals=True,
    use_uv_coords=True,
    use_colors=True,
    in_place_anim=True, 
    vertex_anim_as_deltas=True, 
    anim_as_image=True,
    export_binary=False):
    
    sce = context.scene #bpy.data.scenes[0]

    with open(filepath, 'wb') as file:
        file.write(export_scene_json(sce, export_binary).encode('utf-8'))
    
    """obs = [ob for ob in sce.objects if (ob.type == 'MESH') and (ob.select)]

    # if nothing is selected, export everything
    if len(obs) == 0:
        obs = [ob for ob in sce.objects if ob.type == 'MESH']
    
    data_string = "{\"scene\":1,\"fps\":%i,\"objs\":[" % (25) # Fixed for now
    
    ob_string = ""
    for ob in obs:
        me = ob.to_mesh(sce, True, "PREVIEW")
        ob_string = "%s,%s" % (ob_string, export_objectJson(ob, me, sce))
        
    data_string = "%s%s]}" % (data_string, ob_string[1:])
    
    with open(filepath, 'wb') as file:
        file.write(data_string.encode('utf-8'))"""

    return "FINISHED"

class ExportJSON(bpy.types.Operator, ExportHelper):
    '''Export objects as a JSON object with normals and texture coordinates.'''
    bl_idname = "export_scene.webgl_json"
    bl_label = "Export JSON"

    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={'HIDDEN'})

    use_modifiers = BoolProperty(name="Apply Modifiers", description="Apply Modifiers to the exported mesh", default=True)
    use_normals = BoolProperty(name="Normals", description="Export Normals for smooth and hard shaded faces", default=True)
    use_uv_coords = BoolProperty(name="UVs", description="Export the active UV layer", default=True)
    use_colors = BoolProperty(name="Vertex Colors", description="Export the active vertex color layer", default=True)
    in_place_anim = BoolProperty(name="InPlace Anim", description="Normalize animation for in-place animation", default=True)
    vertex_anim_as_deltas = BoolProperty(name="Vertex Deltas", description="Export vertex position changes as deltas", default=True)
    anim_as_image = BoolProperty(name="Anim on Image", description="Export animation data as an embedded image for shader animations", default=True)
    export_binary = BoolProperty(name="Export mostly binary", description="Export most arrays as Base64 encoded arrays", default=False)

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
        row = layout.row()
        row.prop(self, "in_place_anim")
        row.prop(self, "vertex_anim_as_deltas")
        row = layout.row()
        row.prop(self, "anim_as_image")
        row.prop(self, "export_binary")
        

def menu_func_export(self, context):
    #self.layout.operator(ExportWebgl.bl_idname, text="WebGL (.js)") # unmaintained
    self.layout.operator(ExportJSON.bl_idname, text="WebGL JSON (.json)")


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()