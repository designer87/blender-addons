# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import sys, os
import subprocess

import bpy

from netrender.utils import *

BLENDER_PATH = sys.argv[0]

def reset(job):
    main_file = job.files[0]
    
    job_full_path = main_file.filepath

    if os.path.exists(job_full_path + ".bak"):
        os.remove(job_full_path) # repathed file
        os.renames(job_full_path + ".bak", job_full_path)

def update(job):
    paths = []
    
    main_file = job.files[0]
    
    job_full_path = main_file.filepath

        
    path, ext = os.path.splitext(job_full_path)
    
    new_path = path + ".remap" + ext 
    
    # Disable for now. Partial repath should work anyway
    #all = main_file.filepath != main_file.original_path
    all = False 
    
    for rfile in job.files[1:]:
        if all or rfile.original_path != rfile.filepath:
            paths.append(rfile.original_path)
            paths.append(rfile.filepath)
    
    # Only update if needed
    if paths:        
        process = subprocess.Popen([BLENDER_PATH, "-b", "-noaudio", job_full_path, "-P", __file__, "--", new_path] + paths, stdout=sys.stdout, stderr=subprocess.STDOUT)
        process.wait()
        
        os.renames(job_full_path, job_full_path + ".bak")
        os.renames(new_path, job_full_path)

def process(paths):
    path_map = {}
    for i in range(0, len(paths), 2):
        # special case for point cache
        if paths[i].endswith(".bphys"):
            path, filename = os.path.split(paths[i+1])
            cache_name = filename.split("_")[0]
            path_map[cache_name] = path
        # special case for fluids
        elif paths[i].endswith(".bobj.gz"):
            path_map[os.path.split(paths[i])[0]] = os.path.split(paths[i+1])[0]
        else:
            path_map[os.path.split(paths[i])[1]] = paths[i+1]
            
    # TODO original paths aren't really the original path, they are the normalized path
    # so we repath using the filenames only. 
    
    ###########################
    # LIBRARIES
    ###########################
    for lib in bpy.data.libraries:
        file_path = bpy.path.abspath(lib.filepath)
        new_path = path_map.get(os.path.split(file_path)[1], None)
        if new_path:
            lib.filepath = new_path

    ###########################
    # IMAGES
    ###########################
    for image in bpy.data.images:
        if image.source == "FILE" and not image.packed_file:
            file_path = bpy.path.abspath(image.filepath)
            new_path = path_map.get(os.path.split(file_path)[1], None)
            if new_path:
                image.filepath = new_path
            

    ###########################
    # FLUID + POINT CACHE
    ###########################
    def pointCacheFunc(object, owner, point_cache):
        if not point_cache.use_disk_cache:
            return

        cache_name = cacheName(object, point_cache)
        new_path = path_map.get(cache_name, None)
        if new_path:
            point_cache.use_external = True
            point_cache.filepath = new_path
            point_cache.name = cache_name
        
    def fluidFunc(object, modifier, cache_path):
        fluid = modifier.settings
        new_path = path_map.get(cache_path, None)
        if new_path:
            fluid.path = new_path
        
    def multiresFunc(object, modifier, cache_path):
        new_path = path_map.get(cache_path, None)
        if new_path:
            modifier.filepath = new_path
        
    processObjectDependencies(pointCacheFunc, fluidFunc, multiresFunc)
                

if __name__ == "__main__":
    try:
        i = sys.argv.index("--")
    except:
        i = 0
    
    if i:
        new_path = sys.argv[i+1]
        args = sys.argv[i+2:]
        
        process(args)
        
        bpy.ops.wm.save_as_mainfile(filepath=new_path, check_existing=False)
