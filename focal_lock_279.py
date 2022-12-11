# Nikita Akimov
# interplanety@interplanety.org
#
# GitHub
#    https://github.com/Korchy/blender_focal_lock_279

import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty
from bpy.types import AddonPreferences, Camera, Object, Operator, Panel, PropertyGroup, Scene
from bpy.app.handlers import persistent
from bpy.utils import register_class, unregister_class
import math

bl_info = {
    "name": "Focal Lock",
    "description": "Locks object in a camera's plane of focus",
    "author": "Nikita Akimov, Paul Kotelevets, Anson Savage <artstation.com/ansonsavage>, "
              "Nathan Craddock <nathancraddock.com>",
    "version": (1, 3, 1),
    "blender": (2, 79, 0),
    "location": "Properties area > Render tab > Focal Lock",
    "doc_url": "https://github.com/Korchy/blender_focal_lock_279",
    "tracker_url": "https://github.com/Korchy/blender_focal_lock_279",
    "support": "COMMUNITY",
    "category": "Camera",
    }


# HELPER FUNCTIONS

def distance_to_plane(ob):
    context = bpy.context
    scene = context.scene
    cam = scene.camera
    # Special thanks to batFINGER's answer here:
    # https://blender.stackexchange.com/questions/231817/how-to-obtain-the-vector-normal-to-the-camera-plane
    cam_axis = cam.matrix_world.to_3x3().normalized().col[2]
    cam_axis.negate()
    cam_loc = cam.matrix_world.translation
    v = ob.matrix_world.translation - cam_loc
    n = v.project(cam_axis)
    return n.length


def camera_track_constraint(context):
    # get camera track_to constraint
    return next((c for c in context.scene.camera.constraints if c.type == 'TRACK_TO'), None)


def update_shift_lock(context, camera_obj, x=False, y=False):
    # shift lock correction for camera
    if camera_obj:
        if y:
            shift_diff = round(camera_obj.data.shift_y, 3) - round(camera_obj.data.shift_lock.shift_y, 3)
            camera_obj.rotation_euler[0] = camera_obj.data.shift_lock.cam_rot_x - \
                                           round(math.atan(0.915 * shift_diff), 3)
                                           # round(math.atan(camera_obj.data.shift_y), 3)

            # shift_diff = round(camera_obj.data.shift_lock.shift_y, 3) - round(camera_obj.data.shift_y, 3)
            # if shift_diff:
            #     camera_obj.data.shift_lock.shift_y = camera_obj.data.shift_y
            #     camera_obj.rotation_euler[0] += round(math.atan(shift_diff), 3)
        if x:
            shift_diff = round(camera_obj.data.shift_x, 3) - round(camera_obj.data.shift_lock.shift_x, 3)
            camera_obj.rotation_euler[2] = camera_obj.data.shift_lock.cam_rot_x - \
                                           round(math.atan(0.915 * shift_diff), 3)


def shift_lock_clear(context):
    # clear shift lock parameters
    context.scene.camera.data.shift_lock.shift_x = context.scene.camera.data.shift_x
    context.scene.camera.data.shift_lock.shift_y = context.scene.camera.data.shift_y
    context.scene.camera.data.shift_lock.cam_rot_x = context.scene.camera.rotation_euler[0]


# WATCHER FUNCTIONS

def update_focus_object(self, context):
    settings = self
    update_enable_lock(self, context)   # run this so that all the original settings are made again
    # here's where all the code should go when the focus object is updated!
    if settings.enable_track:
        camera_track_constraint(context).target = settings.focus_object


# There is a bug here - when you enable the focus lock without having an object selected for
# tracking settings.focus_object is None. Shouldn't be too hard to fix though, just don't
# do anything when it is None :)
def update_enable_lock(self, context):
    settings = self
    enable_lock = settings.enable_lock

    # clear all other if 'auto reset' option is on
    if enable_lock and context.user_preferences.addons[__name__].preferences.auto_reset:
        clear_all_other(context=context)

    if enable_lock and settings.focus_object is not None:
        # Set original focal length
        # okay, figure out how to make this apply to just our camera
        settings.original_focal_length = context.scene.camera.data.lens
        # set current distance
        settings.original_distance = distance_to_plane(settings.focus_object)
        settings.focal_distance_ratio = settings.original_focal_length / settings.original_distance


def update_enable_track(self, context):
    settings = self
    # because you are only accessing enable_track once, no need to store in variable
    if settings.enable_track:
        track_constraint = context.scene.camera.constraints.new(type='TRACK_TO')
        track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
        track_constraint.up_axis = 'UP_Y'
        track_constraint.target = settings.focus_object
    else:
        track_constraint = camera_track_constraint(context)
        if track_constraint:
            context.scene.camera.constraints.remove(track_constraint)


@persistent
def update_focal_length(*agrs):
    context = bpy.context
    if context.user_preferences.addons[__name__].preferences.update_only_active:
        # only for active camera
        cameras = [context.scene.camera.data]
    else:
        # for each camera with focal_lock enabled...
        cameras = bpy.data.cameras[:]
    for camera in cameras:
        if camera.focal_lock.enable_lock and camera.focal_lock.focus_object is not None:
            current_distance = distance_to_plane(camera.focal_lock.focus_object)
            camera.lens = current_distance * camera.focal_lock.focal_distance_ratio

    # shift lock
    if context.scene.shift_lock_y or context.scene.shift_lock_x:
        update_shift_lock(
            camera_obj=context.scene.camera,
            context=context,
            y=context.scene.shift_lock_y,
            x=context.scene.shift_lock_x
        )

    # refresh screen
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            area.tag_redraw()


def clear_all_other(context, clear_active=False):
    # clear all enable lock options for all cameras except current camera
    for cam in context.blend_data.cameras:
        if cam.name != context.scene.camera.data.name or clear_active:
            if cam.focal_lock.enable_lock:
                cam.focal_lock.enable_lock = False


# OPERATORS

class BakeFocalLength(Operator):
    bl_idname = "wm.bake_focal_length"
    bl_label = "Bake Focal Length"

    def execute(self, context):
        scene = context.scene
        cam = scene.camera
        for frame in range(context.scene.frame_start, context.scene.frame_end + 1):
            scene.frame_set(frame)
            cam.data.keyframe_insert(data_path="lens")
        return {'FINISHED'}


class ClearBakeFocalLength(Operator):
    bl_idname = "wm.clear_bake_focal_length"
    bl_label = "Clear Bake"

    def execute(self, context):
        scene = context.scene
        cam = scene.camera
        for frame in range(context.scene.frame_start, context.scene.frame_end + 1):
            scene.frame_set(frame)
            cam.data.keyframe_delete(data_path="lens")
        return {'FINISHED'}


class FOCAL_LOCK_OT_clear_all(Operator):
    bl_idname = "focal_lock.clear_all"
    bl_label = "Clear All"
    bl_options = {'REGISTER', 'UNDO'}

    clear_active = BoolProperty(
        default=False
    )

    def execute(self, context):
        clear_all_other(
            context=context,
            clear_active=self.clear_active
        )
        return {'FINISHED'}


# PANELS

class FOCALLOCK_PT_FocalLock(Panel):
    bl_idname = 'focal_lock.panel'
    bl_category = "Focal Lock"
    bl_label = "Focal Lock"
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.scene.camera and context.active_object == context.scene.camera

    def draw_header(self, context):
        cam = context.scene.camera.data
        settings = cam.focal_lock
        layout = self.layout
        layout.active = settings.enable_lock
        layout.prop(settings, "enable_lock", text="")

    def draw(self, context):
        cam = context.scene.camera.data
        settings = cam.focal_lock
        layout = self.layout

        col = layout.column()
        col.enabled = settings.enable_lock

        # Property to set the focus object
        col.prop(settings, "focus_object", text="Focus Object")

        # Mechanics
        # col.prop(settings, 'enable_lock')
        col.prop(settings, 'enable_track')
        sub = col.column(align=True)
        sub.prop(cam, 'lens', text="Focal Length")

        # update only for active camera
        layout.prop(
            data=context.user_preferences.addons[__name__].preferences,
            property='update_only_active'
        )

        # auto reset
        layout.prop(
            data=context.user_preferences.addons[__name__].preferences,
            property='auto_reset'
        )

        # clear all other
        cams = len(context.blend_data.cameras)
        cams_locked = len([c for c in context.blend_data.cameras if c.focal_lock.enable_lock])
        layout.label(text='Enabled on ' + str(cams_locked) + '/' + str(cams))
        layout.operator(
            operator='focal_lock.clear_all',
            text='Clear All Other'
        )


class FOCALLOCK_PT_shift_lock(Panel):
    bl_idname = 'focal_lock.shift_lock'
    bl_category = 'Shift Lock'
    bl_label = 'Shift Lock'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    @classmethod
    def poll(cls, context):
        return context.scene.camera and context.active_object == context.scene.camera

    def draw(self, context):
        layout = self.layout
        layout.prop(
            data=context.scene,
            property='shift_lock_y'
        )
        # layout.prop(
        #     data=context.scene,
        #     property='shift_lock_x'
        # )


class FOCALLOCK_PT_BakeSettings(Panel):
    # COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}
    bl_category = "Focal Lock"
    bl_label = "Focal Lock Baking"
    bl_parent_id = "FOCALLOCK_PT_FocalLock"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'PROPERTIES'
    bl_region_type = "WINDOW"
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.scene.camera and context.active_object == context.scene.camera

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.bake_focal_length")
        layout.operator("wm.clear_bake_focal_length")
        layout.label(text="Bake focal length keyframes for active camera")


# PROPERTIES

class FocalLockSettings(PropertyGroup):
    # These "original" properties aren't ever exposed to the UI.
    # It's not a huge thing, but there is another way to store this without the overhead
    # of making a FloatProperty.
    original_distance = FloatProperty(
        name="Original Distance",
        description="This is the distance that the camera originally was from the focus object",
        )
    original_focal_length = FloatProperty(
        name="Original Focal Length",
        description="The focal length when the user clicked enabled",
        )
    focal_distance_ratio = FloatProperty(
        name="Focal Distance Ratio",
        description="Ratio of the original focal length over the original distance",
        )
    focus_object = PointerProperty(
        name="Focus Object",
        type=Object,
        description="The object you would like the camera to focus on",
        update=lambda self, context: update_focus_object(self=self, context=context)
        )
    enable_lock = BoolProperty(
        name="Lock",
        description="Lock camera zoom to focus object",
        default=False,
        update=lambda self, context: update_enable_lock(self=self, context=context)
        )
    enable_track = BoolProperty(
        name="Track camera to object",
        description="Add a tracking constraint to camera so it always stays focussed on the object",
        default=False,
        update=lambda self, context: update_enable_track(self=self, context=context)
        )


class ShiftLockProps(PropertyGroup):
    shift_x = FloatProperty(
        name='shift X value'
        )
    shift_y = FloatProperty(
        name='shift Y value'
        )
    cam_rot_x = FloatProperty(
        name='Camera X rotation'
    )


# PREFERENCES

class FOCALLOCK_preferences(AddonPreferences):
    bl_idname = __name__

    update_only_active = BoolProperty(
        name='Update only for active camera',
        default=True
    )

    auto_reset = BoolProperty(
        name='Autoreset',
        default=True
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "update_only_active")
        layout.prop(self, "auto_reset")


# REGISTRATION AND UNREGISTRATION

classes = (
    FOCALLOCK_preferences,
    FOCALLOCK_PT_FocalLock,
    FocalLockSettings,
    ShiftLockProps,
    BakeFocalLength,
    ClearBakeFocalLength,
    FOCALLOCK_PT_shift_lock,
    FOCALLOCK_PT_BakeSettings,
    FOCAL_LOCK_OT_clear_all
    )

handlers = [bpy.app.handlers.scene_update_post, bpy.app.handlers.frame_change_post, bpy.app.handlers.load_post]


def register():
    for cls in classes:
        register_class(cls)

    Camera.focal_lock = PointerProperty(type=FocalLockSettings)

    Scene.shift_lock_y = BoolProperty(
        name='Shift Lock Y',
        default=False,
        update=lambda self, context: shift_lock_clear(context=context)
    )
    Scene.shift_lock_x = BoolProperty(
        name='Shift Lock X',
        default=False,
        update=lambda self, context: shift_lock_clear(context=context)
    )
    Camera.shift_lock = PointerProperty(type=ShiftLockProps)

    for handler in handlers:
        [handler.remove(h) for h in handler if h.__name__ == "update_focal_length"]
        handler.append(update_focal_length)


def unregister():
    for cls in classes:
        unregister_class(cls)

    del Camera.shift_lock
    del Scene.shift_lock_y
    del Scene.shift_lock_x
    del Camera.focal_lock

    for handler in handlers:
        [handler.remove(h) for h in handler if h.__name__ == "update_focal_length"]


if __name__ == "__main__":
    register()
